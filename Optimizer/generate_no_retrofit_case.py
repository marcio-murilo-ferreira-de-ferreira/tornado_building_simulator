#!/usr/bin/env python3
from pathlib import Path

from forensic_retrofit_optimizer import AbaqusScriptGenerator, RetrofitCandidate, calculate_design_uplift


def main():
    root = Path('/Users/rebeccanapolitano/antigravityProjects/tornadoSims/codex')
    load = calculate_design_uplift()
    gen = AbaqusScriptGenerator()
    baseline = RetrofitCandidate(strategy='N')
    script = gen.build_model(
        baseline,
        load['force_n'],
        model_name='NoRetrofitBaseline',
        job_name='no_retrofit_base',
        submit_job=False,
    )
    out = root / 'abaqus_run_N.py'
    out.write_text(script, encoding='utf-8')
    print(f'Wrote {out}')


if __name__ == '__main__':
    main()
