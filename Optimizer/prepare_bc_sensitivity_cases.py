#!/usr/bin/env python3
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

BASE = {
    'wall': 0.25,
    'joist': 0.20,
    'anchor': 0.15,
    'friction': 0.5,
    'ramp': 0.05,
}

CASES = {
    'base': {'mesh_scale': 1.0, 'friction': 0.5, 'ramp': 0.05},
    'mesh_coarse': {'mesh_scale': 1.25, 'friction': 0.5, 'ramp': 0.05},
    'mesh_fine': {'mesh_scale': 0.75, 'friction': 0.5, 'ramp': 0.05},
    'fric_low': {'mesh_scale': 1.0, 'friction': 0.3, 'ramp': 0.05},
    'fric_high': {'mesh_scale': 1.0, 'friction': 0.7, 'ramp': 0.05},
    'ramp_fast': {'mesh_scale': 1.0, 'friction': 0.5, 'ramp': 0.02},
    'ramp_slow': {'mesh_scale': 1.0, 'friction': 0.5, 'ramp': 0.10},
    'combo_worst': {'mesh_scale': 1.25, 'friction': 0.3, 'ramp': 0.02},
    'combo_best': {'mesh_scale': 0.75, 'friction': 0.7, 'ramp': 0.10},
}


def replace_once(text, pattern, repl):
    out, n = re.subn(pattern, repl, text, count=1, flags=re.MULTILINE)
    if n != 1:
        raise RuntimeError(f'Pattern not found exactly once: {pattern}')
    return out


def patch_script(text, strategy, case_name, params):
    mesh = params['mesh_scale']
    friction = params['friction']
    ramp = params['ramp']

    job = f'sens_{strategy}_{case_name}'
    model = f'Sensitivity_{strategy.upper()}_{case_name}'

    text = replace_once(text, r'^MODEL_NAME = ".*"$', f'MODEL_NAME = "{model}"')
    text = replace_once(text, r"mdb\.Job\(name='[^']+'", f"mdb.Job(name='{job}'")

    text = replace_once(
        text,
        r"table=\(\(0\.5,\),\)",
        f"table=(({friction:.6f},),)",
    )
    text = replace_once(
        text,
        r"ExplicitDynamicsStep\(name='GustStep', previous='Initial', timePeriod=0\.05\)",
        f"ExplicitDynamicsStep(name='GustStep', previous='Initial', timePeriod={ramp:.6f})",
    )

    text = replace_once(
        text,
        r"p_wall\.seedPart\(size=[0-9.]+, deviationFactor=0\.1, minSizeFactor=0\.1\)",
        f"p_wall.seedPart(size={BASE['wall'] * mesh:.6f}, deviationFactor=0.1, minSizeFactor=0.1)",
    )
    text = replace_once(
        text,
        r"p_joist\.seedPart\(size=[0-9.]+, deviationFactor=0\.1, minSizeFactor=0\.1\)",
        f"p_joist.seedPart(size={BASE['joist'] * mesh:.6f}, deviationFactor=0.1, minSizeFactor=0.1)",
    )

    if strategy == 'b':
        text = replace_once(
            text,
            r"p_plate\.seedPart\(size=[0-9.]+, deviationFactor=0\.1, minSizeFactor=0\.1\)",
            f"p_plate.seedPart(size={BASE['anchor'] * mesh:.6f}, deviationFactor=0.1, minSizeFactor=0.1)",
        )
        text = replace_once(
            text,
            r"p_bolt\.seedPart\(size=[0-9.]+, deviationFactor=0\.1, minSizeFactor=0\.1\)",
            f"p_bolt.seedPart(size={BASE['anchor'] * mesh:.6f}, deviationFactor=0.1, minSizeFactor=0.1)",
        )
    else:
        text = replace_once(
            text,
            r"p_pin\.seedPart\(size=[0-9.]+, deviationFactor=0\.1, minSizeFactor=0\.1\)",
            f"p_pin.seedPart(size={BASE['anchor'] * mesh:.6f}, deviationFactor=0.1, minSizeFactor=0.1)",
        )

    return job, text


def main():
    templates = {
        'b': ROOT / 'abaqus_run_B.py',
        'c': ROOT / 'abaqus_run_C.py',
    }

    for strategy, path in templates.items():
        src = path.read_text(encoding='utf-8')
        for case_name, params in CASES.items():
            job, patched = patch_script(src, strategy, case_name, params)
            out = ROOT / f'sensitivity_run_{strategy}_{case_name}.py'
            out.write_text(patched, encoding='utf-8')
            print(f'wrote {out.name} job={job}')


if __name__ == '__main__':
    main()
