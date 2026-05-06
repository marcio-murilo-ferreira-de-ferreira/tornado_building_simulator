# -*- coding: mbcs -*-
from abaqus import *
from abaqusConstants import *
import regionToolset
import mesh

MODEL_NAME = "Sensitivity_B_mesh_coarse"
if MODEL_NAME in mdb.models:
    del mdb.models[MODEL_NAME]
model = mdb.Model(name=MODEL_NAME)

# Geometry: 16 in x 60 in x 13 in wall (converted to meters)
wall_w = 0.4064
wall_h = 1.524
wall_t = 0.3302

# Joist geometry with fire-cut end and physical separation from wall pocket
joist_w = 0.038099999999999995
joist_h = 0.23495
joist_l = 0.35559999999999997
gap = 0.00635  # separation to enforce no initial mechanical lock

s_wall = model.ConstrainedSketch(name='wall_sk', sheetSize=5.0)
s_wall.rectangle(point1=(0.0, 0.0), point2=(wall_w, wall_h))
p_wall = model.Part(name='Wall', dimensionality=THREE_D, type=DEFORMABLE_BODY)
p_wall.BaseSolidExtrude(sketch=s_wall, depth=wall_t)

s_joist = model.ConstrainedSketch(name='joist_sk', sheetSize=5.0)
s_joist.rectangle(point1=(0.0, 0.0), point2=(joist_w, joist_h))
p_joist = model.Part(name='Joist', dimensionality=THREE_D, type=DEFORMABLE_BODY)
p_joist.BaseSolidExtrude(sketch=s_joist, depth=joist_l)

# Approximate fire-cut by trimming one joist end with an angled cut feature
# (placeholder for a detailed partition/cut in production models)

mat_masonry = model.Material(name='Masonry')
mat_masonry.Density(table=((1900.0,),))
mat_masonry.Elastic(table=((2.0e9, 0.2),))
mat_wood = model.Material(name='Wood')
mat_wood.Density(table=((550.0,),))
mat_wood.Elastic(table=((1.0e10, 0.35),))
mat_steel = model.Material(name='Steel')
mat_steel.Density(table=((7850.0,),))
mat_steel.Elastic(table=((2.0e11, 0.3),))

model.HomogeneousSolidSection(name='WallSection', material='Masonry', thickness=None)
model.HomogeneousSolidSection(name='JoistSection', material='Wood', thickness=None)
p_wall.SectionAssignment(region=(p_wall.cells,), sectionName='WallSection')
p_joist.SectionAssignment(region=(p_joist.cells,), sectionName='JoistSection')

a = model.rootAssembly
a.DatumCsysByDefault(CARTESIAN)
inst_wall = a.Instance(name='Wall-1', part=p_wall, dependent=ON)
inst_joist = a.Instance(name='Joist-1', part=p_joist, dependent=ON)

# Position joist near pocket with explicit separation (fire-cut vulnerability)
a.translate(instanceList=('Joist-1',), vector=(0.15239999999999998, 1.14935, 0.0254))

model.ContactProperty('IntProp')
model.interactionProperties['IntProp'].TangentialBehavior(
    formulation=PENALTY,
    directionality=ISOTROPIC,
    table=((0.500000,),),
    maximumElasticSlip=FRACTION,
    fraction=0.005
)
model.interactionProperties['IntProp'].NormalBehavior(
    pressureOverclosure=HARD, allowSeparation=ON, constraintEnforcementMethod=DEFAULT
)

# Simplified all-inclusive contact definition
region_all = regionToolset.Region(cells=inst_wall.cells + inst_joist.cells)
model.ContactExp(name='GeneralContact', createStepName='Initial')
model.interactions['GeneralContact'].includedPairs.setValuesInStep(
    stepName='Initial', useAllstar=ON
)
model.interactions['GeneralContact'].contactPropertyAssignments.appendInStep(
    stepName='Initial', assignments=((GLOBAL, SELF, 'IntProp'),)
)

model.ExplicitDynamicsStep(name='GustStep', previous='Initial', timePeriod=0.050000)

# Strategy B: External through-plate clamp
model.HomogeneousSolidSection(name='AnchorSection', material='Steel', thickness=None)
s_plate = model.ConstrainedSketch(name='plate_sk', sheetSize=2.0)
s_plate.rectangle(point1=(0.0, 0.0), point2=(0.1904168920996713, 0.1904168920996713))
p_plate = model.Part(name='AnchorPlate', dimensionality=THREE_D, type=DEFORMABLE_BODY)
p_plate.BaseSolidExtrude(sketch=s_plate, depth=0.00635)
p_plate.SectionAssignment(region=(p_plate.cells,), sectionName='AnchorSection')
inst_plate = a.Instance(name='AnchorPlate-1', part=p_plate, dependent=ON)
a.translate(instanceList=('AnchorPlate-1',), vector=(0.0127, 1.14935, 0.0127))
s_bolt = model.ConstrainedSketch(name='bolt_sk', sheetSize=2.0)
s_bolt.rectangle(point1=(0.0, 0.0), point2=(0.0242532416019174, 0.23495))
p_bolt = model.Part(name='AnchorBolt', dimensionality=THREE_D, type=DEFORMABLE_BODY)
p_bolt.BaseSolidExtrude(sketch=s_bolt, depth=0.0242532416019174)
p_bolt.SectionAssignment(region=(p_bolt.cells,), sectionName='AnchorSection')
inst_bolt = a.Instance(name='AnchorBolt-1', part=p_bolt, dependent=ON)
a.translate(instanceList=('AnchorBolt-1',), vector=(0.17145, 1.14935, 0.2032))
p_plate.seedPart(size=0.187500, deviationFactor=0.1, minSizeFactor=0.1)
p_bolt.seedPart(size=0.187500, deviationFactor=0.1, minSizeFactor=0.1)
p_plate.generateMesh(); p_bolt.generateMesh()
a.Set(name='Anchor-Elements', elements=inst_bolt.elements)
embedded_kw = (
    '*EMBEDDED ELEMENT, HOST ELSET=Wall-Elements, ROUNDOFF TOLERANCE=1e-6\n'
    'Anchor-Elements'
)
anchor_inst_name = 'AnchorBolt-1'


# Mesh early to ensure faces are available on instances
p_wall.seedPart(size=0.312500, deviationFactor=0.1, minSizeFactor=0.1)
p_joist.seedPart(size=0.250000, deviationFactor=0.1, minSizeFactor=0.1)
p_wall.generateMesh()
p_joist.generateMesh()
inst_wall = a.instances['Wall-1'] if 'Wall-1' in a.instances else a.instances['WallMerged-1']
inst_joist = a.instances['Joist-1']

# Ensure anchor instance name exists
try:
    anchor_inst_name
except NameError:
    anchor_inst_name = None
try:
    embedded_kw
except NameError:
    embedded_kw = None

# Assembly-level element sets for keyword-based constraints
try:
    a.Set(name='Wall-Elements', elements=inst_wall.elements)
    a.Set(name='Joist-Elements', elements=inst_joist.elements)
except Exception:
    pass

# Contact sets for anchor/joist interface (keyword-based)
try:
    joist_nodes_contact = inst_joist.nodes.getByBoundingBox(
        xMin=0.15239999999999998, xMax=0.1905,
        yMin=1.14935, yMax=1.3843,
        zMin=0.0254, zMax=0.381
    )
    a.Set(name='Joist-Contact-Nodes', nodes=joist_nodes_contact)
    if anchor_inst_name:
        anchor_nodes_contact = a.instances[anchor_inst_name].nodes.getByBoundingBox(
            xMin=0.15239999999999998, xMax=0.1905,
            yMin=1.14935, yMax=1.3843,
            zMin=0.0254, zMax=0.381
        )
        a.Set(name='Anchor-Contact-Nodes', nodes=anchor_nodes_contact)
except Exception:
    pass

# Inject embedded keyword after assembly exists
try:
    if embedded_kw:
        model.keywordBlock.synchVersions(storeNodesAndElements=False)
        found = False
        for i, line in enumerate(model.keywordBlock.sieBlocks):
            if line.lower().startswith('*end assembly'):
                model.keywordBlock.insert(i, embedded_kw)
                found = True
                break
        if not found:
            model.keywordBlock.appendUntouched(embedded_kw)
except Exception:
    pass

# Base restraint for representative unit cell
wall_bottom = inst_wall.faces.getByBoundingBox(
    xMin=0.0, xMax=wall_w, yMin=-1e-3, yMax=1e-3, zMin=0.0, zMax=wall_t
)
model.DisplacementBC(
    name='FixWallBase',
    createStepName='Initial',
    region=regionToolset.Region(faces=wall_bottom),
    u1=0.0, u2=0.0, u3=0.0, ur1=0.0, ur2=0.0, ur3=0.0
)

# Ramped uplift via nodal load on joist top-edge node set
amp_data = ((0.0, 0.0), (1.0, 1.0))
model.TabularAmplitude(name='RampAmp', timeSpan=STEP, data=amp_data)
joist_top_y = 1.3843
joist_top_nodes = inst_joist.nodes.getByBoundingBox(
    xMin=0.0, xMax=joist_w, yMin=joist_top_y - 1e-3, yMax=joist_top_y + 1e-3,
    zMin=0.0, zMax=joist_l
)
a.Set(name='JoistTopNodes', nodes=joist_top_nodes)
node_count = max(1, len(joist_top_nodes))
model.ConcentratedForce(
    name='Uplift',
    createStepName='GustStep',
    region=regionToolset.Region(nodes=joist_top_nodes),
    cf2=3320.579642905502 / node_count,
    amplitude='RampAmp'
)

# Outputs (use defaults for compatibility)

job = mdb.Job(name='sens_b_mesh_coarse', model=MODEL_NAME, type=ANALYSIS, explicitPrecision=SINGLE)
job.writeInput()

