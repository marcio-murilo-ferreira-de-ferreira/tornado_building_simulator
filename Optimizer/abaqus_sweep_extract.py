#!/usr/bin/env python
import argparse
import glob
import json
import os

from odbAccess import openOdb


def extract_job(job):
    row = {
        "job": job,
        "status": "missing",
        "max_u2": None,
        "max_smax": None,
        "min_smin": None,
    }
    odb_path = job + ".odb"
    if not os.path.exists(odb_path):
        log_path = job + ".log"
        if os.path.exists(log_path):
            try:
                tail = open(log_path, "r").read()[-4000:]
                row["status"] = "no_odb"
                row["log_tail"] = tail
            except Exception:
                row["status"] = "no_odb"
        return row

    try:
        odb = openOdb(path=odb_path, readOnly=True)
        step = odb.steps["GustStep"]
        frame = step.frames[-1]
        u = frame.fieldOutputs["U"]
        s = frame.fieldOutputs["S"]
        row["max_u2"] = float(max(abs(v.data[1]) for v in u.values))
        row["max_smax"] = float(max(v.maxPrincipal for v in s.values))
        row["min_smin"] = float(min(v.minPrincipal for v in s.values))
        row["status"] = "ok"
        odb.close()
    except Exception as exc:
        row["status"] = "extract_error"
        row["error"] = str(exc)

    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pattern", default="retrofit_*_h*", help="Job prefix glob")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    jobs = sorted(
        set(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(args.pattern + ".inp"))
    )
    data = {"results": [extract_job(j) for j in jobs]}
    with open(args.out, "w") as f:
        json.dump(data, f, indent=2)
    print("Wrote", args.out, "with", len(data["results"]), "rows")


if __name__ == "__main__":
    main()
