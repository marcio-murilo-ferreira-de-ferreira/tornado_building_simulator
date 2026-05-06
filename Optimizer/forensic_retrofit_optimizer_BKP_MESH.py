#!/usr/bin/env python3
"""Parametric optimization framework for historic masonry roof uplift retrofits.

This script provides:
1) Tributary-area wind uplift load calculation.
2) Candidate generation for three retrofit strategies.
3) Abaqus Python script generation for a representative unit cell.
4) Mock solver and fitness evaluation (safety + historic impact).
5) Multi-objective optimization and Pareto frontier extraction.
"""

import json
import math
import random
from typing import Dict, List, Tuple


IN_TO_M = 0.0254
LBF_TO_N = 4.4482216152605


def calculate_design_uplift(
    span_ft: float = 40.0, spacing_in: float = 16.0, wind_speed_mph: float = 135.0
) -> Dict[str, float]:
    """Compute design uplift force using simplified ASCE-7 C&C suction.

    Formula:
        F_lbf = 0.6 * 0.00256 * V^2 * (Span/2) * (Spacing/12)
    """
    force_lbf = (
        0.6
        * 0.00256
        * wind_speed_mph**2
        * (span_ft / 2.0)
        * (spacing_in / 12.0)
    )
    force_n = force_lbf * LBF_TO_N
    return {
        "span_ft": span_ft,
        "spacing_in": spacing_in,
        "wind_speed_mph": wind_speed_mph,
        "force_lbf": force_lbf,
        "force_n": force_n,
    }


class RetrofitCandidate:
    def __init__(
        self,
        strategy,  # 'A'..'H' or 'N' (no-retrofit baseline)
        embedment_depth_in=0.0,  # A
        rod_diameter_in=0.0,  # A
        plate_size_in=0.0,  # B
        bolt_diameter_in=0.0,  # B
        angle_deg=0.0,  # C
        embedment_length_in=0.0,  # C
        strap_width_in=0.0,  # D
        strap_thickness_in=0.0,  # D
        strap_leg_length_in=0.0,  # D
        uplift_plate_width_in=0.0,  # E
        uplift_plate_thickness_in=0.0,  # E
        screw_diameter_in=0.0,  # E
        holdown_height_in=0.0,  # F, G
        holdown_thickness_in=0.0,  # F, G
        holdown_bolt_diameter_in=0.0,  # F, G
        hanger_gauge_in=0.0,  # H
        hanger_fastener_count=0.0,  # H
        blocking_length_in=0.0,  # F, H
    ):
        self.strategy = strategy
        self.embedment_depth_in = embedment_depth_in
        self.rod_diameter_in = rod_diameter_in
        self.plate_size_in = plate_size_in
        self.bolt_diameter_in = bolt_diameter_in
        self.angle_deg = angle_deg
        self.embedment_length_in = embedment_length_in
        self.strap_width_in = strap_width_in
        self.strap_thickness_in = strap_thickness_in
        self.strap_leg_length_in = strap_leg_length_in
        self.uplift_plate_width_in = uplift_plate_width_in
        self.uplift_plate_thickness_in = uplift_plate_thickness_in
        self.screw_diameter_in = screw_diameter_in
        self.holdown_height_in = holdown_height_in
        self.holdown_thickness_in = holdown_thickness_in
        self.holdown_bolt_diameter_in = holdown_bolt_diameter_in
        self.hanger_gauge_in = hanger_gauge_in
        self.hanger_fastener_count = hanger_fastener_count
        self.blocking_length_in = blocking_length_in

    def describe(self) -> str:
        if self.strategy == "A":
            return (
                f"Strategy A (Gravity Anchor): depth={self.embedment_depth_in:.1f} in, "
                f"rod_dia={self.rod_diameter_in:.2f} in"
            )
        if self.strategy == "B":
            return (
                f"Strategy B (Clamp): plate={self.plate_size_in:.1f} in, "
                f"bolt_dia={self.bolt_diameter_in:.2f} in"
            )
        if self.strategy == "C":
            return (
                f"Strategy C (Friction Pin): angle={self.angle_deg:.1f} deg, "
                f"embed_len={self.embedment_length_in:.1f} in"
            )
        if self.strategy == "D":
            return (
                f"Strategy D (Hurricane Strap): width={self.strap_width_in:.2f} in, "
                f"thk={self.strap_thickness_in:.3f} in, leg={self.strap_leg_length_in:.1f} in"
            )
        if self.strategy == "E":
            return (
                f"Strategy E (Uplift Plate): width={self.uplift_plate_width_in:.2f} in, "
                f"thk={self.uplift_plate_thickness_in:.3f} in, screw_dia={self.screw_diameter_in:.2f} in"
            )
        if self.strategy == "F":
            return (
                f"Strategy F (Hybrid Rod+Holdown): angle={self.angle_deg:.1f} deg, "
                f"embed_len={self.embedment_length_in:.1f} in, holdown_h={self.holdown_height_in:.1f} in"
            )
        if self.strategy == "G":
            return (
                f"Strategy G (Holdown): h={self.holdown_height_in:.1f} in, "
                f"thk={self.holdown_thickness_in:.3f} in, bolt_dia={self.holdown_bolt_diameter_in:.2f} in"
            )
        if self.strategy == "H":
            return (
                f"Strategy H (Hanger+Blocking): gauge={self.hanger_gauge_in:.3f} in, "
                f"fasteners={self.hanger_fastener_count:.0f}, block_len={self.blocking_length_in:.1f} in"
            )
        if self.strategy == "N":
            return "Strategy N (No Retrofit Baseline)"
        return (
            f"Unknown Strategy ({self.strategy})"
        )

    @staticmethod
    def random_candidate(rng: random.Random) -> "RetrofitCandidate":
        strategy = rng.choice(["A", "B", "C", "D", "E", "F", "G", "H"])
        if strategy == "A":
            return RetrofitCandidate(
                strategy="A",
                embedment_depth_in=rng.uniform(24.0, 60.0),
                rod_diameter_in=rng.uniform(0.5, 1.0),
            )
        if strategy == "B":
            return RetrofitCandidate(
                strategy="B",
                plate_size_in=rng.uniform(4.0, 10.0),
                bolt_diameter_in=rng.uniform(0.5, 1.0),
            )
        if strategy == "C":
            return RetrofitCandidate(
                strategy="C",
                angle_deg=rng.uniform(30.0, 60.0),
                embedment_length_in=rng.uniform(6.0, 12.0),
            )
        if strategy == "D":
            return RetrofitCandidate(
                strategy="D",
                strap_width_in=rng.uniform(1.0, 3.0),
                strap_thickness_in=rng.uniform(0.10, 0.25),
                strap_leg_length_in=rng.uniform(6.0, 14.0),
            )
        if strategy == "E":
            return RetrofitCandidate(
                strategy="E",
                uplift_plate_width_in=rng.uniform(3.0, 8.0),
                uplift_plate_thickness_in=rng.uniform(0.20, 0.60),
                screw_diameter_in=rng.uniform(0.25, 0.50),
            )
        if strategy == "F":
            return RetrofitCandidate(
                strategy="F",
                # Connection detail in references uses a ~22.5 deg diagonal rod.
                angle_deg=rng.uniform(20.0, 30.0),
                embedment_length_in=rng.uniform(8.0, 16.0),
                holdown_height_in=rng.uniform(8.0, 18.0),
                holdown_thickness_in=rng.uniform(0.10, 0.30),
                holdown_bolt_diameter_in=rng.uniform(0.375, 0.75),
                blocking_length_in=rng.uniform(12.0, 24.0),
            )
        if strategy == "G":
            return RetrofitCandidate(
                strategy="G",
                holdown_height_in=rng.uniform(8.0, 20.0),
                holdown_thickness_in=rng.uniform(0.10, 0.30),
                holdown_bolt_diameter_in=rng.uniform(0.375, 0.75),
            )
        return RetrofitCandidate(
            strategy="H",
            hanger_gauge_in=rng.uniform(0.045, 0.125),
            hanger_fastener_count=rng.randint(8, 20),
            blocking_length_in=rng.uniform(10.0, 22.0),
        )

    def mutate(self, rng: random.Random, sigma: float = 0.15) -> "RetrofitCandidate":
        child = RetrofitCandidate(**self.__dict__)

        def jitter(value: float, lo: float, hi: float) -> float:
            span = hi - lo
            return max(lo, min(hi, value + rng.gauss(0.0, sigma * span)))

        if child.strategy == "A":
            child.embedment_depth_in = jitter(child.embedment_depth_in, 24.0, 60.0)
            child.rod_diameter_in = jitter(child.rod_diameter_in, 0.5, 1.0)
        elif child.strategy == "B":
            child.plate_size_in = jitter(child.plate_size_in, 4.0, 10.0)
            child.bolt_diameter_in = jitter(child.bolt_diameter_in, 0.5, 1.0)
        elif child.strategy == "C":
            child.angle_deg = jitter(child.angle_deg, 30.0, 60.0)
            child.embedment_length_in = jitter(child.embedment_length_in, 6.0, 12.0)
        elif child.strategy == "D":
            child.strap_width_in = jitter(child.strap_width_in, 1.0, 3.0)
            child.strap_thickness_in = jitter(child.strap_thickness_in, 0.10, 0.25)
            child.strap_leg_length_in = jitter(child.strap_leg_length_in, 6.0, 14.0)
        elif child.strategy == "E":
            child.uplift_plate_width_in = jitter(child.uplift_plate_width_in, 3.0, 8.0)
            child.uplift_plate_thickness_in = jitter(child.uplift_plate_thickness_in, 0.20, 0.60)
            child.screw_diameter_in = jitter(child.screw_diameter_in, 0.25, 0.50)
        elif child.strategy == "F":
            child.angle_deg = jitter(child.angle_deg, 20.0, 30.0)
            child.embedment_length_in = jitter(child.embedment_length_in, 8.0, 16.0)
            child.holdown_height_in = jitter(child.holdown_height_in, 8.0, 18.0)
            child.holdown_thickness_in = jitter(child.holdown_thickness_in, 0.10, 0.30)
            child.holdown_bolt_diameter_in = jitter(child.holdown_bolt_diameter_in, 0.375, 0.75)
            child.blocking_length_in = jitter(child.blocking_length_in, 12.0, 24.0)
        elif child.strategy == "G":
            child.holdown_height_in = jitter(child.holdown_height_in, 8.0, 20.0)
            child.holdown_thickness_in = jitter(child.holdown_thickness_in, 0.10, 0.30)
            child.holdown_bolt_diameter_in = jitter(child.holdown_bolt_diameter_in, 0.375, 0.75)
        elif child.strategy == "H":
            child.hanger_gauge_in = jitter(child.hanger_gauge_in, 0.045, 0.125)
            child.hanger_fastener_count = round(jitter(child.hanger_fastener_count, 8.0, 20.0))
            child.blocking_length_in = jitter(child.blocking_length_in, 10.0, 22.0)
        return child


class AbaqusScriptGenerator:
    def build_model(
        self,
        candidate: RetrofitCandidate,
        applied_load_n: float,
        model_name: str = "RetrofitUnitCell",
        job_name: str = "retrofit_unitcell",
        submit_job: bool = False,
    ) -> str:
        """Return an Abaqus/CAE Python script as a string.

        The script is intentionally generic but valid in structure for Abaqus scripting.
        """
        strategy_block = self._strategy_block(candidate)
        submit_block = (
            "job.writeInput()\n"
            f"inp_name = '{job_name}.inp'\n"
            "with open(inp_name, 'r') as f:\n"
            "    lines = f.readlines()\n"
            "clean = []\n"
            "for line in lines:\n"
            "    if line.strip().lower().startswith('*conflicts'):\n"
            "        continue\n"
            "    clean.append(line)\n"
            "with open(inp_name, 'w') as f:\n"
            "    f.writelines(clean)\n"
            "import os\n"
            f"os.system('abaqus job={job_name} input={job_name}.inp ask_delete=OFF')\n"
            if submit_job
            else (
                "job.writeInput()\n"
                f"inp_name = '{job_name}.inp'\n"
                "with open(inp_name, 'r') as f:\n"
                "    lines = f.readlines()\n"
                "clean = []\n"
                "for line in lines:\n"
                "    if line.strip().lower().startswith('*conflicts'):\n"
                "        continue\n"
                "    clean.append(line)\n"
                "with open(inp_name, 'w') as f:\n"
                "    f.writelines(clean)\n"
            )
        )
        return f'''# -*- coding: mbcs -*-
from abaqus import *
from abaqusConstants import *
import regionToolset
import mesh

MODEL_NAME = "{model_name}"
if MODEL_NAME in mdb.models:
    del mdb.models[MODEL_NAME]
model = mdb.Model(name=MODEL_NAME)

# Geometry: 16 in x 60 in x 13 in wall (converted to meters)
wall_w = {16.0 * IN_TO_M}
wall_h = {60.0 * IN_TO_M}
wall_t = {13.0 * IN_TO_M}

# Joist geometry with fire-cut end and physical separation from wall pocket
joist_w = {1.5 * IN_TO_M}
joist_h = {9.25 * IN_TO_M}
joist_l = {14.0 * IN_TO_M}
gap = {0.25 * IN_TO_M}  # separation to enforce no initial mechanical lock

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
a.translate(instanceList=('Joist-1',), vector=({6.0 * IN_TO_M}, {45.0 * IN_TO_M + 0.25 * IN_TO_M}, {1.0 * IN_TO_M}))

model.ContactProperty('IntProp')
model.interactionProperties['IntProp'].TangentialBehavior(
    formulation=PENALTY,
    directionality=ISOTROPIC,
    table=((0.5,),),
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

model.ExplicitDynamicsStep(name='GustStep', previous='Initial', timePeriod=0.05)

{strategy_block}

# Mesh early to ensure faces are available on instances
p_wall.seedPart(size=0.25, deviationFactor=0.1, minSizeFactor=0.1)
p_joist.seedPart(size=0.20, deviationFactor=0.1, minSizeFactor=0.1)
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
        xMin={6.0 * IN_TO_M}, xMax={7.5 * IN_TO_M},
        yMin={45.0 * IN_TO_M + 0.25 * IN_TO_M}, yMax={45.0 * IN_TO_M + 0.25 * IN_TO_M + 9.25 * IN_TO_M},
        zMin={1.0 * IN_TO_M}, zMax={15.0 * IN_TO_M}
    )
    a.Set(name='Joist-Contact-Nodes', nodes=joist_nodes_contact)
    if anchor_inst_name:
        anchor_nodes_contact = a.instances[anchor_inst_name].nodes.getByBoundingBox(
            xMin={6.0 * IN_TO_M}, xMax={7.5 * IN_TO_M},
            yMin={45.0 * IN_TO_M + 0.25 * IN_TO_M}, yMax={45.0 * IN_TO_M + 0.25 * IN_TO_M + 9.25 * IN_TO_M},
            zMin={1.0 * IN_TO_M}, zMax={15.0 * IN_TO_M}
        )
        a.Set(name='Anchor-Contact-Nodes', nodes=anchor_nodes_contact)
except Exception:
    pass

# Inject embedded keyword after assembly exists
try:
    # Disabled: keyword placement for embedded elements is brittle across Abaqus versions.
    # Keep models runnable for visualization/extraction workflows.
    embedded_kw = None
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
joist_top_y = {45.0 * IN_TO_M + 0.25 * IN_TO_M + 9.25 * IN_TO_M}
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
    cf2={applied_load_n} / node_count,
    amplitude='RampAmp'
)

# Outputs (use defaults for compatibility)

job = mdb.Job(name='{job_name}', model=MODEL_NAME, type=ANALYSIS, explicitPrecision=SINGLE)
{submit_block}
'''

    def _strategy_block(self, candidate: RetrofitCandidate) -> str:
        # Anchor geometry (prisms) + embedded keyword (bonded to masonry). Contact with joist via node surfaces.
        anchor_common = (
            "model.HomogeneousSolidSection(name='AnchorSection', material='Steel', thickness=None)\n"
        )
        if candidate.strategy == "N":
            return (
                "# Strategy N: No retrofit baseline (no anchor hardware)\n"
                "anchor_inst_name = None\n"
                "embedded_kw = None\n"
            )
        if candidate.strategy == "A":
            depth_m = candidate.embedment_depth_in * IN_TO_M
            rod_d = candidate.rod_diameter_in * IN_TO_M
            wall_h = 60.0 * IN_TO_M
            return (
                "# Strategy A: Vertical core anchor\n"
                + anchor_common +
                "s_rod = model.ConstrainedSketch(name='rod_sk', sheetSize=2.0)\n"
                f"s_rod.rectangle(point1=(0.0, 0.0), point2=({rod_d}, {depth_m}))\n"
                "p_rod = model.Part(name='AnchorRod', dimensionality=THREE_D, type=DEFORMABLE_BODY)\n"
                f"p_rod.BaseSolidExtrude(sketch=s_rod, depth={rod_d})\n"
                "p_rod.SectionAssignment(region=(p_rod.cells,), sectionName='AnchorSection')\n"
                "inst_rod = a.Instance(name='AnchorRod-1', part=p_rod, dependent=ON)\n"
                # Place rod fully inside wall by dropping from top of unit cell.
                f"a.translate(instanceList=('AnchorRod-1',), vector=({6.0 * IN_TO_M + 0.5 * (1.5 * IN_TO_M)}, {wall_h - depth_m}, {1.0 * IN_TO_M + 0.5 * (14.0 * IN_TO_M)}))\n"
                "p_rod.seedPart(size=0.15, deviationFactor=0.1, minSizeFactor=0.1)\n"
                "p_rod.generateMesh()\n"
                "a.Set(name='Anchor-Elements', elements=inst_rod.elements)\n"
                "embedded_kw = (\n"
                "    '*EMBEDDED ELEMENT, HOST ELSET=Wall-Elements, ROUNDOFF TOLERANCE=1e-6\\n'\n"
                "    'Anchor-Elements'\n"
                ")\n"
                "anchor_inst_name = 'AnchorRod-1'\n"
            )
        if candidate.strategy == "B":
            plate = candidate.plate_size_in * IN_TO_M
            bolt_d = candidate.bolt_diameter_in * IN_TO_M
            bolt_h = 9.25 * IN_TO_M
            return (
                "# Strategy B: External through-plate clamp\n"
                + anchor_common +
                "s_plate = model.ConstrainedSketch(name='plate_sk', sheetSize=2.0)\n"
                f"s_plate.rectangle(point1=(0.0, 0.0), point2=({plate}, {plate}))\n"
                "p_plate = model.Part(name='AnchorPlate', dimensionality=THREE_D, type=DEFORMABLE_BODY)\n"
                f"p_plate.BaseSolidExtrude(sketch=s_plate, depth={0.25 * IN_TO_M})\n"
                "p_plate.SectionAssignment(region=(p_plate.cells,), sectionName='AnchorSection')\n"
                "inst_plate = a.Instance(name='AnchorPlate-1', part=p_plate, dependent=ON)\n"
                f"a.translate(instanceList=('AnchorPlate-1',), vector=({0.5 * IN_TO_M}, {45.0 * IN_TO_M + 0.25 * IN_TO_M}, {0.5 * IN_TO_M}))\n"
                "s_bolt = model.ConstrainedSketch(name='bolt_sk', sheetSize=2.0)\n"
                f"s_bolt.rectangle(point1=(0.0, 0.0), point2=({bolt_d}, {bolt_h}))\n"
                "p_bolt = model.Part(name='AnchorBolt', dimensionality=THREE_D, type=DEFORMABLE_BODY)\n"
                f"p_bolt.BaseSolidExtrude(sketch=s_bolt, depth={bolt_d})\n"
                "p_bolt.SectionAssignment(region=(p_bolt.cells,), sectionName='AnchorSection')\n"
                "inst_bolt = a.Instance(name='AnchorBolt-1', part=p_bolt, dependent=ON)\n"
                f"a.translate(instanceList=('AnchorBolt-1',), vector=({6.0 * IN_TO_M + 0.5 * (1.5 * IN_TO_M)}, {45.0 * IN_TO_M + 0.25 * IN_TO_M}, {1.0 * IN_TO_M + 0.5 * (14.0 * IN_TO_M)}))\n"
                "p_plate.seedPart(size=0.15, deviationFactor=0.1, minSizeFactor=0.1)\n"
                "p_bolt.seedPart(size=0.15, deviationFactor=0.1, minSizeFactor=0.1)\n"
                "p_plate.generateMesh(); p_bolt.generateMesh()\n"
                "a.Set(name='Anchor-Elements', elements=inst_bolt.elements)\n"
                "embedded_kw = (\n"
                "    '*EMBEDDED ELEMENT, HOST ELSET=Wall-Elements, ROUNDOFF TOLERANCE=1e-6\\n'\n"
                "    'Anchor-Elements'\n"
                ")\n"
                "anchor_inst_name = 'AnchorBolt-1'\n"
            )
        if candidate.strategy == "C":
            # Strategy C: Diagonal adhesive friction pin
            pin_d = 0.625 * IN_TO_M
            length_m = candidate.embedment_length_in * IN_TO_M
            return (
                "# Strategy C: Diagonal adhesive friction pin\n"
                + anchor_common +
                "s_pin = model.ConstrainedSketch(name='pin_sk', sheetSize=2.0)\n"
                f"s_pin.rectangle(point1=(0.0, 0.0), point2=({pin_d}, {length_m}))\n"
                "p_pin = model.Part(name='AnchorPin', dimensionality=THREE_D, type=DEFORMABLE_BODY)\n"
                f"p_pin.BaseSolidExtrude(sketch=s_pin, depth={pin_d})\n"
                "p_pin.SectionAssignment(region=(p_pin.cells,), sectionName='AnchorSection')\n"
                "inst_pin = a.Instance(name='AnchorPin-1', part=p_pin, dependent=ON)\n"
                f"a.translate(instanceList=('AnchorPin-1',), vector=({6.0 * IN_TO_M + 0.5 * (1.5 * IN_TO_M)}, {45.0 * IN_TO_M + 0.25 * IN_TO_M + 0.5 * 9.25 * IN_TO_M - 0.5 * length_m}, {1.0 * IN_TO_M + 0.5 * (14.0 * IN_TO_M)}))\n"
                "p_pin.seedPart(size=0.15, deviationFactor=0.1, minSizeFactor=0.1)\n"
                "p_pin.generateMesh()\n"
                "a.Set(name='Anchor-Elements', elements=inst_pin.elements)\n"
                "embedded_kw = (\n"
                "    '*EMBEDDED ELEMENT, HOST ELSET=Wall-Elements, ROUNDOFF TOLERANCE=1e-6\\n'\n"
                "    'Anchor-Elements'\n"
                ")\n"
                "anchor_inst_name = 'AnchorPin-1'\n"
            )
        if candidate.strategy == "D":
            strap_w = candidate.strap_width_in * IN_TO_M
            strap_t = candidate.strap_thickness_in * IN_TO_M
            strap_leg = candidate.strap_leg_length_in * IN_TO_M
            return (
                "# Strategy D: Hurricane strap (steel strap linking joist to masonry)\n"
                + anchor_common +
                "s_strap = model.ConstrainedSketch(name='strap_sk', sheetSize=2.0)\n"
                f"s_strap.rectangle(point1=(0.0, 0.0), point2=({strap_w}, {strap_leg}))\n"
                "p_strap = model.Part(name='AnchorStrap', dimensionality=THREE_D, type=DEFORMABLE_BODY)\n"
                f"p_strap.BaseSolidExtrude(sketch=s_strap, depth={strap_t})\n"
                "p_strap.SectionAssignment(region=(p_strap.cells,), sectionName='AnchorSection')\n"
                "inst_strap = a.Instance(name='AnchorStrap-1', part=p_strap, dependent=ON)\n"
                f"a.translate(instanceList=('AnchorStrap-1',), vector=({6.0 * IN_TO_M - 0.5 * strap_w}, {45.0 * IN_TO_M + 0.25 * IN_TO_M - 0.25 * strap_leg}, {1.0 * IN_TO_M + 0.4 * (14.0 * IN_TO_M)}))\n"
                "p_strap.seedPart(size=0.12, deviationFactor=0.1, minSizeFactor=0.1)\n"
                "p_strap.generateMesh()\n"
                "a.Set(name='Anchor-Elements', elements=inst_strap.elements)\n"
                "embedded_kw = (\n"
                "    '*EMBEDDED ELEMENT, HOST ELSET=Wall-Elements, ROUNDOFF TOLERANCE=1e-6\\n'\n"
                "    'Anchor-Elements'\n"
                ")\n"
                "anchor_inst_name = 'AnchorStrap-1'\n"
            )
        if candidate.strategy == "E":
            plate_w = candidate.uplift_plate_width_in * IN_TO_M
            plate_t = candidate.uplift_plate_thickness_in * IN_TO_M
            screw_d = candidate.screw_diameter_in * IN_TO_M
            screw_l = 6.0 * IN_TO_M
            return (
                "# Strategy E: Uplift plate with screws at joist seat\n"
                + anchor_common +
                "s_up = model.ConstrainedSketch(name='uplift_plate_sk', sheetSize=2.0)\n"
                f"s_up.rectangle(point1=(0.0, 0.0), point2=({plate_w}, {plate_w}))\n"
                "p_up = model.Part(name='AnchorUpliftPlate', dimensionality=THREE_D, type=DEFORMABLE_BODY)\n"
                f"p_up.BaseSolidExtrude(sketch=s_up, depth={plate_t})\n"
                "p_up.SectionAssignment(region=(p_up.cells,), sectionName='AnchorSection')\n"
                "inst_up = a.Instance(name='AnchorUpliftPlate-1', part=p_up, dependent=ON)\n"
                f"a.translate(instanceList=('AnchorUpliftPlate-1',), vector=({6.0 * IN_TO_M - 0.5 * plate_w}, {45.0 * IN_TO_M + 0.25 * IN_TO_M + 0.5 * 9.25 * IN_TO_M - 0.5 * plate_w}, {1.0 * IN_TO_M}))\n"
                "s_scr = model.ConstrainedSketch(name='uplift_screw_sk', sheetSize=2.0)\n"
                f"s_scr.rectangle(point1=(0.0, 0.0), point2=({screw_d}, {screw_l}))\n"
                "p_scr = model.Part(name='AnchorScrew', dimensionality=THREE_D, type=DEFORMABLE_BODY)\n"
                f"p_scr.BaseSolidExtrude(sketch=s_scr, depth={screw_d})\n"
                "p_scr.SectionAssignment(region=(p_scr.cells,), sectionName='AnchorSection')\n"
                "inst_scr = a.Instance(name='AnchorScrew-1', part=p_scr, dependent=ON)\n"
                f"a.translate(instanceList=('AnchorScrew-1',), vector=({6.0 * IN_TO_M + 0.5 * (1.5 * IN_TO_M)}, {45.0 * IN_TO_M + 0.25 * IN_TO_M + 0.5 * 9.25 * IN_TO_M - 0.5 * screw_l}, {1.0 * IN_TO_M + 0.3 * (14.0 * IN_TO_M)}))\n"
                "p_up.seedPart(size=0.12, deviationFactor=0.1, minSizeFactor=0.1)\n"
                "p_scr.seedPart(size=0.12, deviationFactor=0.1, minSizeFactor=0.1)\n"
                "p_up.generateMesh(); p_scr.generateMesh()\n"
                "a.Set(name='Anchor-Elements', elements=inst_scr.elements)\n"
                "embedded_kw = (\n"
                "    '*EMBEDDED ELEMENT, HOST ELSET=Wall-Elements, ROUNDOFF TOLERANCE=1e-6\\n'\n"
                "    'Anchor-Elements'\n"
                ")\n"
                "anchor_inst_name = 'AnchorScrew-1'\n"
            )
        if candidate.strategy == "F":
            # Hybrid: diagonal epoxy rod + holdown leg + blocking proxy.
            pin_d = max(0.5 * IN_TO_M, candidate.holdown_bolt_diameter_in * IN_TO_M)
            length_m = candidate.embedment_length_in * IN_TO_M
            hold_h = candidate.holdown_height_in * IN_TO_M
            hold_t = candidate.holdown_thickness_in * IN_TO_M
            block_l = candidate.blocking_length_in * IN_TO_M
            return (
                "# Strategy F: Hybrid rod + holdown + blocking\n"
                + anchor_common +
                "s_pin = model.ConstrainedSketch(name='hy_pin_sk', sheetSize=2.0)\n"
                f"s_pin.rectangle(point1=(0.0, 0.0), point2=({pin_d}, {length_m}))\n"
                "p_pin = model.Part(name='HybridPin', dimensionality=THREE_D, type=DEFORMABLE_BODY)\n"
                f"p_pin.BaseSolidExtrude(sketch=s_pin, depth={pin_d})\n"
                "p_pin.SectionAssignment(region=(p_pin.cells,), sectionName='AnchorSection')\n"
                "inst_pin = a.Instance(name='HybridPin-1', part=p_pin, dependent=ON)\n"
                f"a.translate(instanceList=('HybridPin-1',), vector=({6.0 * IN_TO_M + 0.5 * (1.5 * IN_TO_M)}, {45.0 * IN_TO_M + 0.25 * IN_TO_M + 0.4 * 9.25 * IN_TO_M - 0.5 * length_m}, {1.0 * IN_TO_M + 0.5 * (14.0 * IN_TO_M)}))\n"
                "s_hold = model.ConstrainedSketch(name='hy_hold_sk', sheetSize=2.0)\n"
                f"s_hold.rectangle(point1=(0.0, 0.0), point2=({hold_t}, {hold_h}))\n"
                "p_hold = model.Part(name='HybridHoldown', dimensionality=THREE_D, type=DEFORMABLE_BODY)\n"
                f"p_hold.BaseSolidExtrude(sketch=s_hold, depth={1.5 * IN_TO_M})\n"
                "p_hold.SectionAssignment(region=(p_hold.cells,), sectionName='AnchorSection')\n"
                "inst_hold = a.Instance(name='HybridHoldown-1', part=p_hold, dependent=ON)\n"
                f"a.translate(instanceList=('HybridHoldown-1',), vector=({6.0 * IN_TO_M - hold_t}, {45.0 * IN_TO_M + 0.25 * IN_TO_M}, {1.0 * IN_TO_M + 0.2 * (14.0 * IN_TO_M)}))\n"
                "s_blk = model.ConstrainedSketch(name='hy_block_sk', sheetSize=2.0)\n"
                f"s_blk.rectangle(point1=(0.0, 0.0), point2=({1.5 * IN_TO_M}, {9.25 * IN_TO_M}))\n"
                "p_blk = model.Part(name='HybridBlock', dimensionality=THREE_D, type=DEFORMABLE_BODY)\n"
                f"p_blk.BaseSolidExtrude(sketch=s_blk, depth={block_l})\n"
                "p_blk.SectionAssignment(region=(p_blk.cells,), sectionName='AnchorSection')\n"
                "inst_blk = a.Instance(name='HybridBlock-1', part=p_blk, dependent=ON)\n"
                f"a.translate(instanceList=('HybridBlock-1',), vector=({6.0 * IN_TO_M}, {45.0 * IN_TO_M + 0.25 * IN_TO_M}, {1.0 * IN_TO_M + (14.0 * IN_TO_M)}))\n"
                "p_pin.seedPart(size=0.12, deviationFactor=0.1, minSizeFactor=0.1)\n"
                "p_hold.seedPart(size=0.12, deviationFactor=0.1, minSizeFactor=0.1)\n"
                "p_blk.seedPart(size=0.16, deviationFactor=0.1, minSizeFactor=0.1)\n"
                "p_pin.generateMesh(); p_hold.generateMesh(); p_blk.generateMesh()\n"
                "a.Set(name='Anchor-Elements', elements=inst_pin.elements + inst_hold.elements)\n"
                "embedded_kw = (\n"
                "    '*EMBEDDED ELEMENT, HOST ELSET=Wall-Elements, ROUNDOFF TOLERANCE=1e-6\\n'\n"
                "    'Anchor-Elements'\n"
                ")\n"
                "anchor_inst_name = 'HybridHoldown-1'\n"
            )
        if candidate.strategy == "G":
            hold_h = candidate.holdown_height_in * IN_TO_M
            hold_t = candidate.holdown_thickness_in * IN_TO_M
            bolt_d = candidate.holdown_bolt_diameter_in * IN_TO_M
            return (
                "# Strategy G: Discrete holdown\n"
                + anchor_common +
                "s_hold = model.ConstrainedSketch(name='holdown_sk', sheetSize=2.0)\n"
                f"s_hold.rectangle(point1=(0.0, 0.0), point2=({hold_t}, {hold_h}))\n"
                "p_hold = model.Part(name='Holdown', dimensionality=THREE_D, type=DEFORMABLE_BODY)\n"
                f"p_hold.BaseSolidExtrude(sketch=s_hold, depth={1.5 * IN_TO_M})\n"
                "p_hold.SectionAssignment(region=(p_hold.cells,), sectionName='AnchorSection')\n"
                "inst_hold = a.Instance(name='Holdown-1', part=p_hold, dependent=ON)\n"
                f"a.translate(instanceList=('Holdown-1',), vector=({6.0 * IN_TO_M - hold_t}, {45.0 * IN_TO_M + 0.25 * IN_TO_M}, {1.0 * IN_TO_M + 0.1 * (14.0 * IN_TO_M)}))\n"
                "s_bolt = model.ConstrainedSketch(name='holdown_bolt_sk', sheetSize=2.0)\n"
                f"s_bolt.rectangle(point1=(0.0, 0.0), point2=({bolt_d}, {6.0 * IN_TO_M}))\n"
                "p_bolt = model.Part(name='HoldownBolt', dimensionality=THREE_D, type=DEFORMABLE_BODY)\n"
                f"p_bolt.BaseSolidExtrude(sketch=s_bolt, depth={bolt_d})\n"
                "p_bolt.SectionAssignment(region=(p_bolt.cells,), sectionName='AnchorSection')\n"
                "inst_bolt = a.Instance(name='HoldownBolt-1', part=p_bolt, dependent=ON)\n"
                f"a.translate(instanceList=('HoldownBolt-1',), vector=({6.0 * IN_TO_M + 0.5 * (1.5 * IN_TO_M)}, {45.0 * IN_TO_M + 0.25 * IN_TO_M + 0.5 * 9.25 * IN_TO_M - 3.0 * IN_TO_M}, {1.0 * IN_TO_M + 0.25 * (14.0 * IN_TO_M)}))\n"
                "p_hold.seedPart(size=0.12, deviationFactor=0.1, minSizeFactor=0.1)\n"
                "p_bolt.seedPart(size=0.12, deviationFactor=0.1, minSizeFactor=0.1)\n"
                "p_hold.generateMesh(); p_bolt.generateMesh()\n"
                "a.Set(name='Anchor-Elements', elements=inst_hold.elements + inst_bolt.elements)\n"
                "embedded_kw = (\n"
                "    '*EMBEDDED ELEMENT, HOST ELSET=Wall-Elements, ROUNDOFF TOLERANCE=1e-6\\n'\n"
                "    'Anchor-Elements'\n"
                ")\n"
                "anchor_inst_name = 'Holdown-1'\n"
            )
        if candidate.strategy == "H":
            gage_t = candidate.hanger_gauge_in * IN_TO_M
            fast_count = int(max(8, min(20, candidate.hanger_fastener_count)))
            block_l = candidate.blocking_length_in * IN_TO_M
            return (
                "# Strategy H: Hanger + blocking package\n"
                + anchor_common +
                "s_hng = model.ConstrainedSketch(name='hanger_sk', sheetSize=2.0)\n"
                f"s_hng.rectangle(point1=(0.0, 0.0), point2=({gage_t}, {9.25 * IN_TO_M}))\n"
                "p_hng = model.Part(name='Hanger', dimensionality=THREE_D, type=DEFORMABLE_BODY)\n"
                f"p_hng.BaseSolidExtrude(sketch=s_hng, depth={2.5 * IN_TO_M})\n"
                "p_hng.SectionAssignment(region=(p_hng.cells,), sectionName='AnchorSection')\n"
                "inst_hng = a.Instance(name='Hanger-1', part=p_hng, dependent=ON)\n"
                f"a.translate(instanceList=('Hanger-1',), vector=({6.0 * IN_TO_M - gage_t}, {45.0 * IN_TO_M + 0.25 * IN_TO_M}, {1.0 * IN_TO_M}))\n"
                "s_blk = model.ConstrainedSketch(name='hanger_block_sk', sheetSize=2.0)\n"
                f"s_blk.rectangle(point1=(0.0, 0.0), point2=({1.5 * IN_TO_M}, {9.25 * IN_TO_M}))\n"
                "p_blk = model.Part(name='HangerBlock', dimensionality=THREE_D, type=DEFORMABLE_BODY)\n"
                f"p_blk.BaseSolidExtrude(sketch=s_blk, depth={block_l})\n"
                "p_blk.SectionAssignment(region=(p_blk.cells,), sectionName='AnchorSection')\n"
                "inst_blk = a.Instance(name='HangerBlock-1', part=p_blk, dependent=ON)\n"
                f"a.translate(instanceList=('HangerBlock-1',), vector=({6.0 * IN_TO_M}, {45.0 * IN_TO_M + 0.25 * IN_TO_M}, {1.0 * IN_TO_M + (14.0 * IN_TO_M)}))\n"
                "p_hng.seedPart(size=0.12, deviationFactor=0.1, minSizeFactor=0.1)\n"
                "p_blk.seedPart(size=0.15, deviationFactor=0.1, minSizeFactor=0.1)\n"
                "p_hng.generateMesh(); p_blk.generateMesh()\n"
                "a.Set(name='Anchor-Elements', elements=inst_hng.elements)\n"
                "embedded_kw = (\n"
                "    '*EMBEDDED ELEMENT, HOST ELSET=Wall-Elements, ROUNDOFF TOLERANCE=1e-6\\n'\n"
                "    'Anchor-Elements'\n"
                ")\n"
                f"# fastener count proxy retained for reporting: {fast_count}\n"
                "anchor_inst_name = 'Hanger-1'\n"
            )
        # Fallback to no-retrofit if strategy label is unrecognized.
        return (
            "# Fallback baseline (unknown strategy)\n"
            "anchor_inst_name = None\n"
            "embedded_kw = None\n"
        )

    def _anchor_stiffness(self, candidate: RetrofitCandidate) -> float:
        if candidate.strategy == "A":
            return 1.5e7 * (candidate.embedment_depth_in / 60.0) * (candidate.rod_diameter_in / 1.0)
        if candidate.strategy == "B":
            return 3.0e7 * (candidate.plate_size_in / 10.0) * (candidate.bolt_diameter_in / 1.0)
        if candidate.strategy == "C":
            return 5.0e6 * (candidate.embedment_length_in / 12.0) * (candidate.angle_deg / 60.0)
        if candidate.strategy == "D":
            return 1.1e7 * (candidate.strap_width_in / 3.0) * (candidate.strap_thickness_in / 0.25)
        if candidate.strategy == "E":
            return 1.3e7 * (candidate.uplift_plate_width_in / 8.0) * (candidate.screw_diameter_in / 0.50)
        if candidate.strategy == "F":
            return (
                1.8e7
                * (candidate.embedment_length_in / 16.0)
                * (candidate.holdown_height_in / 18.0)
                * (candidate.holdown_bolt_diameter_in / 0.75)
            )
        if candidate.strategy == "G":
            return (
                1.6e7
                * (candidate.holdown_height_in / 20.0)
                * (candidate.holdown_thickness_in / 0.30)
                * (candidate.holdown_bolt_diameter_in / 0.75)
            )
        if candidate.strategy == "H":
            return (
                9.0e6
                * (candidate.hanger_gauge_in / 0.125)
                * (candidate.hanger_fastener_count / 20.0)
                * (candidate.blocking_length_in / 22.0)
            )
        return 0.0


def _volume_removed_in3(candidate: RetrofitCandidate) -> float:
    if candidate.strategy == "A":
        r = candidate.rod_diameter_in / 2.0
        return math.pi * r * r * candidate.embedment_depth_in
    if candidate.strategy == "B":
        # Through-bolt hole + bearing recess proxy
        r = candidate.bolt_diameter_in / 2.0
        wall_thickness_in = 13.0
        hole_vol = math.pi * r * r * wall_thickness_in
        plate_bearing_vol = 0.05 * candidate.plate_size_in**2
        return hole_vol + plate_bearing_vol
    if candidate.strategy == "C":
        # Strategy C diagonal bore
        pin_dia = 0.625
        r = pin_dia / 2.0
        return math.pi * r * r * candidate.embedment_length_in
    if candidate.strategy == "D":
        # Strap with multiple fastener holes through joist and shallow masonry face penetration
        hole_d = 0.25
        return 4.0 * math.pi * (hole_d / 2.0) ** 2 * 2.0
    if candidate.strategy == "E":
        # Uplift plate uses screw penetrations and a small seat recess
        d = max(0.25, candidate.screw_diameter_in)
        screws_vol = 3.0 * math.pi * (d / 2.0) ** 2 * 4.0
        recess_vol = 0.03 * candidate.uplift_plate_width_in**2
        return screws_vol + recess_vol
    if candidate.strategy == "F":
        pin_d = max(0.375, candidate.holdown_bolt_diameter_in)
        pin_vol = math.pi * (pin_d / 2.0) ** 2 * candidate.embedment_length_in
        holdown_slots = 2.0 * math.pi * (0.25 / 2.0) ** 2 * candidate.holdown_height_in
        # Blocking can often be installed with minimal timber loss; keep trim penalty modest.
        block_trim = 0.010 * candidate.blocking_length_in * 1.5 * 9.25
        return pin_vol + holdown_slots + block_trim
    if candidate.strategy == "G":
        d = max(0.375, candidate.holdown_bolt_diameter_in)
        bolt_vol = math.pi * (d / 2.0) ** 2 * 6.0
        seat_slot = 0.03 * candidate.holdown_height_in
        return bolt_vol + seat_slot
    if candidate.strategy == "H":
        d = 0.162
        nails_vol = candidate.hanger_fastener_count * math.pi * (d / 2.0) ** 2 * 2.0
        block_trim = 0.006 * candidate.blocking_length_in * 1.5 * 9.25
        return nails_vol + block_trim
    return 0.0


def evaluate_fitness(
    candidate: RetrofitCandidate, simulation_result: Dict[str, float]
) -> Dict[str, float]:
    """Return safety and historic impact fitness values."""
    displacement_in = simulation_result["displacement_in"]
    resisting_lbf = simulation_result["resisting_force_lbf"]
    required_lbf = simulation_result["required_force_lbf"]

    if displacement_in > 0.5:
        return {
            "safety_score": 0.0,
            "impact_score": float("inf"),
            "pass_fail": 0.0,
            "displacement_in": displacement_in,
            "capacity_margin": resisting_lbf - required_lbf,
        }

    volume = _volume_removed_in3(candidate)
    multiplier_map = {
        "A": 1.0,   # high volume, hidden
        "B": 50.0,  # facade-visible clamp plate
        "C": 2.0,   # low volume, reliability risk
        "D": 12.0,  # visible but reversible strap hardware
        "E": 8.0,   # moderate visibility at seat
        "F": 7.0,   # multi-component, partly concealed, moderate visibility
        "G": 7.0,   # concentrated visible holdown near pocket
        "H": 4.0,   # interior hanger/blocking package, mostly hidden
        "N": 0.0,   # no intervention
    }
    multiplier = multiplier_map.get(candidate.strategy, 10.0)
    impact = volume * multiplier

    # safety score normalized: better margin and lower displacement is better
    margin_ratio = max(0.0, (resisting_lbf - required_lbf) / max(required_lbf, 1e-6))
    safety = 1.0 + margin_ratio - min(1.0, displacement_in / 0.5)

    return {
        "safety_score": safety,
        "impact_score": impact,
        "pass_fail": 1.0,
        "displacement_in": displacement_in,
        "capacity_margin": resisting_lbf - required_lbf,
    }


def mock_abaqus_solver(candidate: RetrofitCandidate, load_lbf: float) -> Dict[str, float]:
    """Physics-inspired mock replacing real Abaqus run."""
    if candidate.strategy == "A":
        # Resisting force proxy: deadweight cone + rod tension component
        depth = candidate.embedment_depth_in
        dia = candidate.rod_diameter_in
        cone_factor = 32.0
        rod_factor = 4200.0
        resisting = cone_factor * depth**1.25 + rod_factor * dia**2
        reliability = 0.92
    elif candidate.strategy == "B":
        plate = candidate.plate_size_in
        bolt = candidate.bolt_diameter_in
        shear_factor = 5200.0
        plate_factor = 250.0
        resisting = shear_factor * bolt**2 + plate_factor * plate
        reliability = 0.98
    elif candidate.strategy == "C":
        angle = candidate.angle_deg
        length = candidate.embedment_length_in
        bond_strength = 85.0
        angle_eff = math.sin(math.radians(angle))
        resisting = bond_strength * length * angle_eff * 20.0
        reliability = 0.72
    elif candidate.strategy == "D":
        width = candidate.strap_width_in
        thk = candidate.strap_thickness_in
        leg = candidate.strap_leg_length_in
        strap_factor = 1600.0
        leg_factor = 220.0
        resisting = strap_factor * width * (thk / 0.125) + leg_factor * leg
        reliability = 0.88
    elif candidate.strategy == "E":
        w = candidate.uplift_plate_width_in
        t = candidate.uplift_plate_thickness_in
        d = candidate.screw_diameter_in
        plate_factor = 450.0
        screw_factor = 11000.0
        resisting = plate_factor * w * (t / 0.25) + screw_factor * d**2
        reliability = 0.90
    elif candidate.strategy == "F":
        angle = candidate.angle_deg
        length = candidate.embedment_length_in
        hold_h = candidate.holdown_height_in
        hold_t = candidate.holdown_thickness_in
        hold_d = candidate.holdown_bolt_diameter_in
        block_l = candidate.blocking_length_in
        rod_component = 70.0 * length * max(0.32, math.sin(math.radians(angle))) * 18.0
        hold_component = 3000.0 * (hold_t / 0.25) * (hold_h / 12.0) + 8000.0 * hold_d**2
        block_component = 90.0 * block_l
        resisting = rod_component + hold_component + block_component
        reliability = 0.94
    elif candidate.strategy == "G":
        hold_h = candidate.holdown_height_in
        hold_t = candidate.holdown_thickness_in
        hold_d = candidate.holdown_bolt_diameter_in
        plate_component = 5600.0 * (hold_t / 0.25) * (hold_h / 12.0)
        bolt_component = 16500.0 * hold_d**2
        resisting = plate_component + bolt_component
        reliability = 0.935
    elif candidate.strategy == "H":
        gage = candidate.hanger_gauge_in
        n_fast = candidate.hanger_fastener_count
        block_l = candidate.blocking_length_in
        hanger_component = 420.0 * n_fast * (gage / 0.08)
        block_component = 120.0 * block_l
        resisting = hanger_component + block_component
        reliability = 0.86
    else:  # N = no retrofit baseline
        resisting = 120.0
        reliability = 0.60

    # Model uplift slip response as ratio-dependent with stochastic scatter
    ratio = load_lbf / max(resisting * reliability, 1.0)
    displacement_in = max(0.0, 0.08 * ratio**1.7)
    displacement_in += random.uniform(0.0, 0.03)

    # Penalize if strongly overloaded
    if ratio > 1.0:
        displacement_in += 0.55 * (ratio - 1.0)

    return {
        "required_force_lbf": load_lbf,
        "resisting_force_lbf": resisting,
        "displacement_in": displacement_in,
    }


def dominates(a: Dict[str, float], b: Dict[str, float]) -> bool:
    better_or_equal = (a["safety_score"] >= b["safety_score"]) and (
        a["impact_score"] <= b["impact_score"]
    )
    strictly_better = (a["safety_score"] > b["safety_score"]) or (
        a["impact_score"] < b["impact_score"]
    )
    return better_or_equal and strictly_better


def pareto_frontier(results: List[Tuple[RetrofitCandidate, Dict[str, float]]]):
    frontier: List[Tuple[RetrofitCandidate, Dict[str, float]]] = []
    for i, (cand_i, fit_i) in enumerate(results):
        if fit_i["pass_fail"] < 1.0:
            continue
        dominated = False
        for j, (_, fit_j) in enumerate(results):
            if i == j:
                continue
            if dominates(fit_j, fit_i):
                dominated = True
                break
        if not dominated:
            frontier.append((cand_i, fit_i))
    frontier.sort(key=lambda x: (x[1]["impact_score"], -x[1]["safety_score"]))
    return frontier


def crossover(p1: RetrofitCandidate, p2: RetrofitCandidate, rng: random.Random) -> RetrofitCandidate:
    # Keep within one strategy for coherent parameter inheritance
    strategy = p1.strategy if rng.random() < 0.5 else p2.strategy
    if p1.strategy != p2.strategy:
        base = p1 if p1.strategy == strategy else p2
        return RetrofitCandidate(**base.__dict__)

    child = RetrofitCandidate(strategy=strategy)
    if strategy == "A":
        child.embedment_depth_in = (p1.embedment_depth_in + p2.embedment_depth_in) / 2.0
        child.rod_diameter_in = p1.rod_diameter_in if rng.random() < 0.5 else p2.rod_diameter_in
    elif strategy == "B":
        child.plate_size_in = (p1.plate_size_in + p2.plate_size_in) / 2.0
        child.bolt_diameter_in = p1.bolt_diameter_in if rng.random() < 0.5 else p2.bolt_diameter_in
    elif strategy == "C":
        child.angle_deg = (p1.angle_deg + p2.angle_deg) / 2.0
        child.embedment_length_in = p1.embedment_length_in if rng.random() < 0.5 else p2.embedment_length_in
    elif strategy == "D":
        child.strap_width_in = (p1.strap_width_in + p2.strap_width_in) / 2.0
        child.strap_thickness_in = p1.strap_thickness_in if rng.random() < 0.5 else p2.strap_thickness_in
        child.strap_leg_length_in = p1.strap_leg_length_in if rng.random() < 0.5 else p2.strap_leg_length_in
    elif strategy == "E":
        child.uplift_plate_width_in = (p1.uplift_plate_width_in + p2.uplift_plate_width_in) / 2.0
        child.uplift_plate_thickness_in = (
            p1.uplift_plate_thickness_in if rng.random() < 0.5 else p2.uplift_plate_thickness_in
        )
        child.screw_diameter_in = p1.screw_diameter_in if rng.random() < 0.5 else p2.screw_diameter_in
    elif strategy == "F":
        child.angle_deg = (p1.angle_deg + p2.angle_deg) / 2.0
        child.embedment_length_in = p1.embedment_length_in if rng.random() < 0.5 else p2.embedment_length_in
        child.holdown_height_in = (p1.holdown_height_in + p2.holdown_height_in) / 2.0
        child.holdown_thickness_in = (
            p1.holdown_thickness_in if rng.random() < 0.5 else p2.holdown_thickness_in
        )
        child.holdown_bolt_diameter_in = (
            p1.holdown_bolt_diameter_in if rng.random() < 0.5 else p2.holdown_bolt_diameter_in
        )
        child.blocking_length_in = (p1.blocking_length_in + p2.blocking_length_in) / 2.0
    elif strategy == "G":
        child.holdown_height_in = (p1.holdown_height_in + p2.holdown_height_in) / 2.0
        child.holdown_thickness_in = (
            p1.holdown_thickness_in if rng.random() < 0.5 else p2.holdown_thickness_in
        )
        child.holdown_bolt_diameter_in = (
            p1.holdown_bolt_diameter_in if rng.random() < 0.5 else p2.holdown_bolt_diameter_in
        )
    elif strategy == "H":
        child.hanger_gauge_in = (p1.hanger_gauge_in + p2.hanger_gauge_in) / 2.0
        child.hanger_fastener_count = (
            p1.hanger_fastener_count if rng.random() < 0.5 else p2.hanger_fastener_count
        )
        child.blocking_length_in = (p1.blocking_length_in + p2.blocking_length_in) / 2.0
    return child


def run_optimization(
    generations: int = 10, population_size: int = 15, seed: int = 42,
    span_ft: float = 40.0, spacing_in: float = 16.0, wind_speed_mph: float = 135.0
) -> Dict[str, object]:
    rng = random.Random(seed)
    load = calculate_design_uplift(span_ft, spacing_in, wind_speed_mph)
    load_lbf = load["force_lbf"]

    population = [RetrofitCandidate.random_candidate(rng) for _ in range(population_size)]
    all_results: List[Tuple[RetrofitCandidate, Dict[str, float]]] = []

    for _ in range(generations):
        scored: List[Tuple[RetrofitCandidate, Dict[str, float]]] = []
        for cand in population:
            sim = mock_abaqus_solver(cand, load_lbf)
            fit = evaluate_fitness(cand, sim)
            scored.append((cand, fit))
            all_results.append((cand, fit))

        # Selection: prioritize pass/fail then safety-impact balance
        impact_weight = 10000.0 / max(load_lbf**2, 1.0)
        scored.sort(
            key=lambda x: (
                x[1]["pass_fail"],
                x[1]["safety_score"] - impact_weight * x[1]["impact_score"],
            ),
            reverse=True,
        )
        elites = [c for c, _ in scored[: max(3, population_size // 4)]]

        next_pop = elites[:]
        while len(next_pop) < population_size:
            p1, p2 = rng.sample(elites, 2) if len(elites) > 1 else (elites[0], elites[0])
            child = crossover(p1, p2, rng)
            if rng.random() < 0.8:
                child = child.mutate(rng)
            if rng.random() < 0.15:
                child = RetrofitCandidate.random_candidate(rng)
            next_pop.append(child)
        population = next_pop[:population_size]

    frontier = pareto_frontier(all_results)
    impact_weight = 10000.0 / max(load_lbf**2, 1.0)
    if not frontier:
        best = max(
            all_results,
            key=lambda x: (x[1]["pass_fail"], x[1]["safety_score"] - x[1]["impact_score"] * 0.001),
        )
    else:
        # pick a compromise: dynamic penalty inversely proportional to demand
        best = max(frontier, key=lambda x: x[1]["safety_score"] / (1.0 + impact_weight * x[1]["impact_score"]))

    return {"load": load, "all_results": all_results, "frontier": frontier, "winner": best}


def _serialize_candidate(candidate: RetrofitCandidate) -> Dict[str, float]:
    return {
        "strategy": candidate.strategy,
        "embedment_depth_in": candidate.embedment_depth_in,
        "rod_diameter_in": candidate.rod_diameter_in,
        "plate_size_in": candidate.plate_size_in,
        "bolt_diameter_in": candidate.bolt_diameter_in,
        "angle_deg": candidate.angle_deg,
        "embedment_length_in": candidate.embedment_length_in,
        "strap_width_in": candidate.strap_width_in,
        "strap_thickness_in": candidate.strap_thickness_in,
        "strap_leg_length_in": candidate.strap_leg_length_in,
        "uplift_plate_width_in": candidate.uplift_plate_width_in,
        "uplift_plate_thickness_in": candidate.uplift_plate_thickness_in,
        "screw_diameter_in": candidate.screw_diameter_in,
        "holdown_height_in": candidate.holdown_height_in,
        "holdown_thickness_in": candidate.holdown_thickness_in,
        "holdown_bolt_diameter_in": candidate.holdown_bolt_diameter_in,
        "hanger_gauge_in": candidate.hanger_gauge_in,
        "hanger_fastener_count": candidate.hanger_fastener_count,
        "blocking_length_in": candidate.blocking_length_in,
    }


def write_full_population(
    results: Dict[str, object], out_path: str = "full_population_results.json"
) -> None:
    payload = {
        "load": results["load"],
        "candidates": [],
    }
    for candidate, fit in results["all_results"]:
        payload["candidates"].append(
            {
                "candidate": _serialize_candidate(candidate),
                "fitness": fit,
            }
        )
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def consultants_recommendation(
    winner: Tuple[RetrofitCandidate, Dict[str, float]], load_lbf: float
) -> str:
    cand, fit = winner
    if cand.strategy == "A":
        strategy_reason = (
            "Deep vertical anchorage engaged enough masonry deadweight while keeping "
            "facade impact minimal."
        )
    elif cand.strategy == "B":
        strategy_reason = (
            "Through-plate clamp provided the strongest mechanical lock, but its facade "
            "visibility is heavily penalized for historic preservation."
        )
    elif cand.strategy == "C":
        strategy_reason = (
            "Diagonal adhesive pin delivered adequate uplift resistance at very low "
            "material removal, creating the best safety-to-preservation tradeoff."
        )
    elif cand.strategy == "D":
        strategy_reason = (
            "Hurricane strap created a direct tensile load path from joist to masonry "
            "with moderate visual impact and strong uplift restraint."
        )
    elif cand.strategy == "E":
        strategy_reason = (
            "Uplift plate increased mechanical lock at the joist seat and improved "
            "capacity while remaining less intrusive than a facade clamp."
        )
    elif cand.strategy == "F":
        strategy_reason = (
            "Hybrid diagonal rod plus holdown provided a redundant load path with "
            "high reliability and balanced preservation impact."
        )
    elif cand.strategy == "G":
        strategy_reason = (
            "Discrete holdown delivered a strong direct tension path with less "
            "masonry intervention than through-wall clamp systems."
        )
    elif cand.strategy == "H":
        strategy_reason = (
            "Hanger and blocking improved local seat restraint and diaphragm transfer "
            "with comparatively low visual impact."
        )
    else:
        strategy_reason = (
            "No retrofit baseline provided reference performance only and does not "
            "satisfy preservation retrofit intent."
        )
    return (
        "Consultant's Recommendation:\n"
        f"Selected {cand.describe()}.\n"
        f"Design uplift demand = {load_lbf:.1f} lbf.\n"
        f"Predicted displacement = {fit['displacement_in']:.3f} in "
        "(limit = 0.5 in), "
        f"capacity margin = {fit['capacity_margin']:.1f} lbf.\n"
        f"Historic impact score = {fit['impact_score']:.2f} (lower is better).\n"
        f"Reasoning: {strategy_reason}"
    )


import io
import sys

def main(span_ft: float = 40.0, spacing_in: float = 16.0, wind_speed_mph: float = 135.0, seed: int = 7) -> str:
    # Capture prints to string buffer for the dashboard console
    old_stdout = sys.stdout
    new_stdout = io.StringIO()
    sys.stdout = new_stdout
    
    try:
        results = run_optimization(
            generations=12, population_size=15, seed=seed,
            span_ft=span_ft, spacing_in=spacing_in, wind_speed_mph=wind_speed_mph
        )

        load = results["load"]
        winner = results["winner"]
        frontier = results["frontier"]

        print("=== Design Uplift Calculation ===")
        print(
            f"Span={load['span_ft']} ft, Spacing={load['spacing_in']} in, "
            f"Wind={load['wind_speed_mph']} mph"
        )
        print(f"Uplift Demand: {load['force_lbf']:.2f} lbf ({load['force_n']:.2f} N)")
        print()

        print("=== Pareto Frontier (Safe Solutions) ===")
        if not frontier:
            print("No pass solutions found on frontier.")
        else:
            for idx, (cand, fit) in enumerate(frontier[:10], 1):
                print(
                    f"{idx:02d}. {cand.describe()} | safety={fit['safety_score']:.3f}, "
                    f"impact={fit['impact_score']:.3f}, disp={fit['displacement_in']:.3f} in"
                )
        print()

        print("=== Winner ===")
        print(consultants_recommendation(winner, load["force_lbf"]))
        print()

        # Produce an Abaqus script for the winner
        gen = AbaqusScriptGenerator()
        winner_candidate = winner[0]
        script_text = gen.build_model(winner_candidate, load["force_n"])
        out_path = "generated_abaqus_winner.py"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(script_text)
        print(f"Abaqus script for winner written to: {out_path}")

        # Write full population for dashboard analytics
        write_full_population(results, "full_population_results.json")
        
        return new_stdout.getvalue()
        
    finally:
        sys.stdout = old_stdout

if __name__ == "__main__":
    print(main())
