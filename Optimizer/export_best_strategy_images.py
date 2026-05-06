#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path


STRATEGIES = ["A", "B", "C", "D", "E", "F", "G", "H"]


def pick_best_by_strategy(full_pop):
    best = {}
    for item in full_pop.get("candidates", []):
        cand = item.get("candidate", {})
        fit = item.get("fitness", {})
        strat = cand.get("strategy")
        if strat not in STRATEGIES:
            continue
        if fit.get("pass_fail", 0.0) < 1.0:
            continue
        score = fit.get("safety_score", 0.0)
        if strat not in best or score > best[strat]["fitness"]["safety_score"]:
            best[strat] = item
    return best


def export_images_for_job(abaqus_cmd, root, jobname, outdir):
    odb_path = root / f"{jobname}.odb"
    if not odb_path.exists():
        return {"job": jobname, "status": "missing_odb"}
    cmd = [
        abaqus_cmd,
        "cae",
        f"noGUI={str(root / 'abaqus_postprocess.py')}",
        "--",
        jobname,
        str(outdir),
    ]
    run = subprocess.run(
        cmd,
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    if run.returncode != 0:
        return {
            "job": jobname,
            "status": "postprocess_error",
            "stderr": run.stderr[-2000:],
            "stdout": run.stdout[-2000:],
        }

    payload = {
        "job": jobname,
        "status": "ok",
        "before": str((outdir / f"{jobname}_before.png").name),
        "u2": str((outdir / f"{jobname}_U.png").name),
        "smax": str((outdir / f"{jobname}_Smax.png").name),
    }
    return payload


def main():
    ap = argparse.ArgumentParser(
        description="Export before/U/S images for best safe case of each strategy."
    )
    ap.add_argument(
        "--root",
        default="/Users/rebeccanapolitano/antigravityProjects/tornadoSims/codex",
    )
    ap.add_argument("--full-pop", default="full_population_results.json")
    ap.add_argument("--outdir", default="fe_images")
    ap.add_argument("--manifest", default="fe_images_manifest.json")
    ap.add_argument("--abaqus-cmd", default="abaqus")
    args = ap.parse_args()

    root = Path(args.root)
    full_path = root / args.full_pop
    outdir = root / args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    if not full_path.exists():
        raise SystemExit(f"Missing full population file: {full_path}")
    full_pop = json.loads(full_path.read_text(encoding="utf-8"))

    best = pick_best_by_strategy(full_pop)
    results = []
    for strat in STRATEGIES:
        jobname = f"retrofit_{strat.lower()}"
        row = {"strategy": strat, "job": jobname}
        row.update(export_images_for_job(args.abaqus_cmd, root, jobname, outdir))
        results.append(row)

    manifest = {"image_dir": args.outdir, "strategies": results}
    manifest_path = root / args.manifest
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {manifest_path}")


if __name__ == "__main__":
    main()
