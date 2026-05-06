from abaqus import session
from visualization import *
from abaqusConstants import (
    COLOR,
    CONTOURS_ON_DEF,
    CONTOURS_ON_UNDEF,
    INTEGRATION_POINT,
    INVARIANT,
    NODAL,
    OFF,
    PNG,
    UNDEFORMED,
)
import sys
import os
import shutil


def pick_step_name_with_frames(odb):
    if "GustStep" in odb.steps and len(odb.steps["GustStep"].frames) > 0:
        return "GustStep"
    for name in odb.steps.keys():
        if len(odb.steps[name].frames) > 0:
            return name
    return list(odb.steps.keys())[-1]


def main():
    if len(sys.argv) < 3:
        raise SystemExit(
            "Usage: abaqus cae noGUI=abaqus_postprocess.py -- <jobname> <outdir>"
        )
    jobname = sys.argv[-2]
    outdir = sys.argv[-1]
    odb_path = jobname + ".odb"
    if not os.path.exists(odb_path):
        raise SystemExit("ODB not found: " + odb_path)
    if not os.path.isdir(outdir):
        os.makedirs(outdir)

    vis_odb = session.openOdb(name=odb_path)
    odb = vis_odb
    step_name = pick_step_name_with_frames(odb)
    step = odb.steps[step_name]
    first_frame_idx = 0
    has_frames = len(step.frames) > 0
    last_frame_idx = len(step.frames) - 1 if has_frames else 0

    vp = session.viewports[session.currentViewportName]
    vp.setValues(displayedObject=vis_odb)
    vp.viewportAnnotationOptions.setValues(triad=OFF, compass=OFF, title=OFF, state=OFF)
    vp.view.fitView()

    session.printOptions.setValues(rendition=COLOR)
    session.pngOptions.setValues(imageSize=(1200, 720))

    # Before load: undeformed model view at first frame.
    vp.odbDisplay.setFrame(step=step_name, frame=first_frame_idx)
    vp.odbDisplay.display.setValues(plotState=(UNDEFORMED,))
    session.printToFile(
        fileName=os.path.join(outdir, jobname + "_before.png"),
        format=PNG,
        canvasObjects=(vp,),
    )

    if not has_frames:
        # No converged/output frames in this ODB: publish graceful placeholders
        # so dashboard still renders per-strategy imagery.
        src = os.path.join(outdir, jobname + "_before.png")
        shutil.copyfile(src, os.path.join(outdir, jobname + "_U.png"))
        shutil.copyfile(src, os.path.join(outdir, jobname + "_Smax.png"))
        odb.close()
        return

    # After load: displacement magnitude contour (deformed).
    vp.odbDisplay.setFrame(step=step_name, frame=last_frame_idx)
    vp.odbDisplay.display.setValues(plotState=(CONTOURS_ON_DEF,))
    vp.odbDisplay.setPrimaryVariable(
        variableLabel="U",
        outputPosition=NODAL,
        refinement=(INVARIANT, "Magnitude"),
    )
    session.printOptions.setValues(rendition=COLOR)
    session.printToFile(
        fileName=os.path.join(outdir, jobname + "_U.png"),
        format=PNG,
        canvasObjects=(vp,),
    )

    # After load: stress contour (max principal on undeformed for readability).
    vp.odbDisplay.display.setValues(plotState=(CONTOURS_ON_UNDEF,))
    vp.odbDisplay.setPrimaryVariable(
        variableLabel="S",
        outputPosition=INTEGRATION_POINT,
        refinement=(INVARIANT, "Max. Principal"),
    )
    session.printToFile(
        fileName=os.path.join(outdir, jobname + "_Smax.png"),
        format=PNG,
        canvasObjects=(vp,),
    )

    odb.close()


main()
