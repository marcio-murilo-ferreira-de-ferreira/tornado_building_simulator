import json
import sys
from odbAccess import openOdb


def pick_step_with_frames(odb):
    if "GustStep" in odb.steps and len(odb.steps["GustStep"].frames) > 0:
        return odb.steps["GustStep"]
    for name in odb.steps.keys():
        if len(odb.steps[name].frames) > 0:
            return odb.steps[name]
    return odb.steps[list(odb.steps.keys())[-1]]


def extract(jobname):
    odb_path = jobname + ".odb"
    odb = openOdb(path=odb_path, readOnly=True)
    step = pick_step_with_frames(odb)
    frame = step.frames[-1]
    u = frame.fieldOutputs["U"]
    s = frame.fieldOutputs["S"]

    max_u2 = max(abs(v.data[1]) for v in u.values)
    max_smax = max(v.maxPrincipal for v in s.values)
    min_smin = min(v.minPrincipal for v in s.values)

    odb.close()
    return {
        "job": jobname,
        "max_u2": float(max_u2),
        "max_smax": float(max_smax),
        "min_smin": float(min_smin),
    }


def main():
    if len(sys.argv) < 3:
        raise SystemExit("Usage: abaqus python abaqus_extract.py -- <jobA> <jobB> ... <out.json>")
    jobs = [j for j in sys.argv[1:-1] if j != "--"]
    out_path = sys.argv[-1]
    data = {"results": [extract(j) for j in jobs]}
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)


main()
