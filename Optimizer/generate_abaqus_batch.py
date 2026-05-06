#!/usr/bin/env python3
import json
from pathlib import Path

from forensic_retrofit_optimizer import AbaqusScriptGenerator, RetrofitCandidate


def pick_best_by_strategy(full_pop):
    best = {}
    target_strategies = ["A", "B", "C", "D", "E", "F", "G", "H"]
    for item in full_pop.get("candidates", []):
        cand = item["candidate"]
        fit = item["fitness"]
        strat = cand.get("strategy")
        if strat not in target_strategies:
            continue
        if fit.get("pass_fail", 0.0) < 1.0:
            continue
        score = fit.get("safety_score", 0.0)
        if strat not in best or score > best[strat]["fitness"]["safety_score"]:
            best[strat] = item
    return best


def to_candidate(c):
    return RetrofitCandidate(
        strategy=c.get("strategy", "A"),
        embedment_depth_in=c.get("embedment_depth_in", 0.0),
        rod_diameter_in=c.get("rod_diameter_in", 0.0),
        plate_size_in=c.get("plate_size_in", 0.0),
        bolt_diameter_in=c.get("bolt_diameter_in", 0.0),
        angle_deg=c.get("angle_deg", 0.0),
        embedment_length_in=c.get("embedment_length_in", 0.0),
        strap_width_in=c.get("strap_width_in", 0.0),
        strap_thickness_in=c.get("strap_thickness_in", 0.0),
        strap_leg_length_in=c.get("strap_leg_length_in", 0.0),
        uplift_plate_width_in=c.get("uplift_plate_width_in", 0.0),
        uplift_plate_thickness_in=c.get("uplift_plate_thickness_in", 0.0),
        screw_diameter_in=c.get("screw_diameter_in", 0.0),
        holdown_height_in=c.get("holdown_height_in", 0.0),
        holdown_thickness_in=c.get("holdown_thickness_in", 0.0),
        holdown_bolt_diameter_in=c.get("holdown_bolt_diameter_in", 0.0),
        hanger_gauge_in=c.get("hanger_gauge_in", 0.0),
        hanger_fastener_count=c.get("hanger_fastener_count", 0.0),
        blocking_length_in=c.get("blocking_length_in", 0.0),
    )


def main():
    root = Path(__file__).resolve().parent
    full_path = root / "full_population_results.json"
    if not full_path.exists():
        raise SystemExit("full_population_results.json not found. Run forensic_retrofit_optimizer.py first.")
    full_pop = json.loads(full_path.read_text(encoding="utf-8"))
    load_n = full_pop["load"]["force_n"]

    best = pick_best_by_strategy(full_pop)
    gen = AbaqusScriptGenerator()

    for strat, item in best.items():
        cand = to_candidate(item["candidate"])
        model_name = f"Retrofit_{strat}"
        job_name = f"retrofit_{strat.lower()}"
        script = gen.build_model(
            cand, load_n, model_name=model_name, job_name=job_name, submit_job=False
        )
        out = root / f"abaqus_run_{strat}.py"
        out.write_text(script, encoding="utf-8")
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()
