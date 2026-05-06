#!/usr/bin/env python3
"""Verification checks for joint modeling sanity and Abaqus result integrity."""

import argparse
import hashlib
import json
import math
import random
from pathlib import Path
from typing import Dict, List, Tuple

from forensic_retrofit_optimizer import (
    RetrofitCandidate,
    calculate_design_uplift,
    evaluate_fitness,
    mock_abaqus_solver,
)


def _mean_mock_response(candidate: RetrofitCandidate, load_lbf: float, samples: int) -> Dict[str, float]:
    displacement = 0.0
    resisting = 0.0
    for i in range(samples):
        random.seed(7100 + i)
        result = mock_abaqus_solver(candidate, load_lbf)
        displacement += result["displacement_in"]
        resisting += result["resisting_force_lbf"]
    return {
        "displacement_in": displacement / samples,
        "resisting_force_lbf": resisting / samples,
        "required_force_lbf": load_lbf,
    }


def _record(name: str, passed: bool, details: str) -> Dict[str, object]:
    return {"name": name, "passed": passed, "details": details}


def _test_load_formula_scaling() -> Dict[str, object]:
    base = calculate_design_uplift(span_ft=40.0, spacing_in=16.0, wind_speed_mph=135.0)["force_lbf"]
    doubled_span = calculate_design_uplift(span_ft=80.0, spacing_in=16.0, wind_speed_mph=135.0)["force_lbf"]
    doubled_spacing = calculate_design_uplift(span_ft=40.0, spacing_in=32.0, wind_speed_mph=135.0)["force_lbf"]
    doubled_wind = calculate_design_uplift(span_ft=40.0, spacing_in=16.0, wind_speed_mph=270.0)["force_lbf"]
    passed = (
        math.isclose(doubled_span / base, 2.0, rel_tol=1e-9)
        and math.isclose(doubled_spacing / base, 2.0, rel_tol=1e-9)
        and math.isclose(doubled_wind / base, 4.0, rel_tol=1e-9)
    )
    return _record(
        "load_formula_scaling",
        passed,
        "Expected linear span/spacing scaling and V^2 wind scaling.",
    )


def _strategy_candidates() -> Dict[str, Tuple[RetrofitCandidate, RetrofitCandidate]]:
    return {
        "A": (
            RetrofitCandidate("A", embedment_depth_in=24.0, rod_diameter_in=0.50),
            RetrofitCandidate("A", embedment_depth_in=60.0, rod_diameter_in=1.00),
        ),
        "B": (
            RetrofitCandidate("B", plate_size_in=4.0, bolt_diameter_in=0.50),
            RetrofitCandidate("B", plate_size_in=10.0, bolt_diameter_in=1.00),
        ),
        "C": (
            RetrofitCandidate("C", angle_deg=30.0, embedment_length_in=6.0),
            RetrofitCandidate("C", angle_deg=60.0, embedment_length_in=12.0),
        ),
        "D": (
            RetrofitCandidate("D", strap_width_in=1.0, strap_thickness_in=0.10, strap_leg_length_in=6.0),
            RetrofitCandidate("D", strap_width_in=3.0, strap_thickness_in=0.25, strap_leg_length_in=14.0),
        ),
        "E": (
            RetrofitCandidate("E", uplift_plate_width_in=3.0, uplift_plate_thickness_in=0.20, screw_diameter_in=0.25),
            RetrofitCandidate("E", uplift_plate_width_in=8.0, uplift_plate_thickness_in=0.60, screw_diameter_in=0.50),
        ),
        "F": (
            RetrofitCandidate(
                "F",
                angle_deg=20.0,
                embedment_length_in=8.0,
                holdown_height_in=8.0,
                holdown_thickness_in=0.10,
                holdown_bolt_diameter_in=0.375,
                blocking_length_in=12.0,
            ),
            RetrofitCandidate(
                "F",
                angle_deg=30.0,
                embedment_length_in=16.0,
                holdown_height_in=18.0,
                holdown_thickness_in=0.30,
                holdown_bolt_diameter_in=0.75,
                blocking_length_in=24.0,
            ),
        ),
        "G": (
            RetrofitCandidate("G", holdown_height_in=8.0, holdown_thickness_in=0.10, holdown_bolt_diameter_in=0.375),
            RetrofitCandidate("G", holdown_height_in=20.0, holdown_thickness_in=0.30, holdown_bolt_diameter_in=0.75),
        ),
        "H": (
            RetrofitCandidate("H", hanger_gauge_in=0.045, hanger_fastener_count=8, blocking_length_in=10.0),
            RetrofitCandidate("H", hanger_gauge_in=0.125, hanger_fastener_count=20, blocking_length_in=22.0),
        ),
    }


def _test_strategy_strength_monotonic(load_lbf: float, samples: int) -> Dict[str, object]:
    offenders: List[str] = []
    for strategy, (weak, strong) in _strategy_candidates().items():
        weak_result = _mean_mock_response(weak, load_lbf, samples)
        strong_result = _mean_mock_response(strong, load_lbf, samples)
        if strong_result["resisting_force_lbf"] <= weak_result["resisting_force_lbf"]:
            offenders.append(f"{strategy}: resisting did not increase")
            continue
        if strong_result["displacement_in"] >= weak_result["displacement_in"]:
            offenders.append(f"{strategy}: displacement did not decrease")
    return _record(
        "strategy_strength_monotonic",
        len(offenders) == 0,
        "All A-H stronger variants should resist more and displace less."
        if not offenders
        else "; ".join(offenders),
    )


def _test_load_response_monotonic(samples: int) -> Dict[str, object]:
    candidate = RetrofitCandidate("F", angle_deg=25.0, embedment_length_in=12.0, holdown_height_in=13.0, holdown_thickness_in=0.20, holdown_bolt_diameter_in=0.50, blocking_length_in=18.0)
    l1 = calculate_design_uplift(wind_speed_mph=90.0)["force_lbf"]
    l2 = calculate_design_uplift(wind_speed_mph=135.0)["force_lbf"]
    l3 = calculate_design_uplift(wind_speed_mph=170.0)["force_lbf"]
    d1 = _mean_mock_response(candidate, l1, samples)["displacement_in"]
    d2 = _mean_mock_response(candidate, l2, samples)["displacement_in"]
    d3 = _mean_mock_response(candidate, l3, samples)["displacement_in"]
    passed = d1 < d2 < d3
    return _record(
        "load_response_monotonic",
        passed,
        f"Expected disp(90mph)<disp(135mph)<disp(170mph); got {d1:.4f}, {d2:.4f}, {d3:.4f} in",
    )


def _test_preservation_tradeoff_exists(load_lbf: float, samples: int) -> Dict[str, object]:
    rng = random.Random(20260227)
    passing: List[Tuple[float, float]] = []
    for _ in range(220):
        cand = RetrofitCandidate.random_candidate(rng)
        sim = _mean_mock_response(cand, load_lbf, samples)
        fit = evaluate_fitness(cand, sim)
        if fit["pass_fail"] >= 1.0:
            passing.append((fit["safety_score"], fit["impact_score"]))

    has_conflict = False
    for s1, i1 in passing:
        for s2, i2 in passing:
            if s1 > s2 and i1 > i2:
                has_conflict = True
                break
        if has_conflict:
            break

    return _record(
        "preservation_tradeoff_exists",
        has_conflict,
        "Found at least one pair where higher safety also has higher historic impact.",
    )


def _test_no_retrofit_failure(load_lbf: float, samples: int) -> Dict[str, object]:
    baseline = RetrofitCandidate("N")
    sim = _mean_mock_response(baseline, load_lbf, samples)
    fit = evaluate_fitness(baseline, sim)
    passed = fit["pass_fail"] < 1.0
    return _record(
        "no_retrofit_fails_design_load",
        passed,
        f"Expected baseline fail under design load; pass_fail={fit['pass_fail']:.1f}, disp={fit['displacement_in']:.3f} in",
    )


def _test_abaqus_results_sanity(root: Path) -> Dict[str, object]:
    path = root / "abaqus_results.json"
    if not path.exists():
        return _record("abaqus_results_sanity", True, "Skipped: abaqus_results.json not found.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    bad: List[str] = []
    for row in payload.get("results", []):
        job = row.get("job", "unknown")
        for key in ("max_u2", "max_smax", "min_smin"):
            value = row.get(key)
            if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
                bad.append(f"{job}:{key}=invalid")
    return _record(
        "abaqus_results_sanity",
        len(bad) == 0,
        "All Abaqus extracted metrics are finite." if not bad else "; ".join(bad),
    )


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _test_image_fallback_detection(root: Path) -> Dict[str, object]:
    manifest_path = root / "fe_images_manifest.json"
    if not manifest_path.exists():
        return _record("image_fallback_detection", True, "Skipped: fe_images_manifest.json not found.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    image_dir = root / manifest.get("image_dir", "fe_images")
    offenders: List[str] = []
    for row in manifest.get("strategies", []):
        if row.get("status") != "ok":
            continue
        job = row.get("job", "unknown")
        before = image_dir / row.get("before", "")
        u2 = image_dir / row.get("u2", "")
        smax = image_dir / row.get("smax", "")
        if not before.exists() or not u2.exists() or not smax.exists():
            offenders.append(f"{job}: missing image files")
            continue
        if _md5(before) == _md5(u2):
            offenders.append(f"{job}: U image equals before (likely fallback)")
        if _md5(before) == _md5(smax):
            offenders.append(f"{job}: Smax image equals before (likely fallback)")
    return _record(
        "image_fallback_detection",
        len(offenders) == 0,
        "No fallback-copy images detected." if not offenders else "; ".join(offenders),
    )


def run_suite(root: Path, samples: int) -> Dict[str, object]:
    load_lbf = calculate_design_uplift()["force_lbf"]
    tests = [
        _test_load_formula_scaling(),
        _test_strategy_strength_monotonic(load_lbf, samples),
        _test_load_response_monotonic(samples),
        _test_preservation_tradeoff_exists(load_lbf, samples),
        _test_no_retrofit_failure(load_lbf, samples),
        _test_abaqus_results_sanity(root),
        _test_image_fallback_detection(root),
    ]
    passed = [t for t in tests if t["passed"]]
    return {
        "summary": {
            "total": len(tests),
            "passed": len(passed),
            "failed": len(tests) - len(passed),
            "design_load_lbf": load_lbf,
        },
        "tests": tests,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run joint verification checks.")
    parser.add_argument("--root", default=".", help="Project root containing Abaqus artifacts.")
    parser.add_argument("--samples", type=int, default=16, help="Monte Carlo samples per mock check.")
    parser.add_argument(
        "--out",
        default="verification_report.json",
        help="Output JSON report path.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    report = run_suite(root, max(4, args.samples))
    out_path = Path(args.out).resolve()
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Verification summary: {report['summary']['passed']}/{report['summary']['total']} passed")
    for test in report["tests"]:
        status = "PASS" if test["passed"] else "FAIL"
        print(f"- {status} {test['name']}: {test['details']}")

    if report["summary"]["failed"] > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
