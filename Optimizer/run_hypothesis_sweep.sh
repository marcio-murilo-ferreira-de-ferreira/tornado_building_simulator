#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$PWD}"
cd "$ROOT"

unset PYTHONHOME PYTHONPATH PYTHONSTARTUP
module purge
module load abaqus/2022
which abaqus

FORCE_N=$(python3 - <<'PY'
import json
with open('full_population_results.json','r') as f:
    d=json.load(f)
print(d['load']['force_n'])
PY
)

echo "Using uplift force N: ${FORCE_N}"

# 1) Generate baseline input files from CAE scripts
for s in A B C; do
  echo "Generating baseline input for strategy ${s}"
  abaqus cae noGUI="abaqus_run_${s}.py" > "gen_${s}.log" 2>&1 || true
  base="retrofit_${s,,}.inp"
  if [[ ! -f "$base" ]]; then
    echo "ERROR: missing baseline input $base"
    exit 1
  fi
done

# 2) Remove old sweep artifacts
python3 - <<'PY'
from pathlib import Path
suffixes = ('.odb','.lck','.prt','.sim','.sta','.dat','.msg','.com','.log','.inp')
for p in Path('.').glob('retrofit_*_h*'):
    if p.suffix in suffixes:
        p.unlink()
PY

# 3) Patch and run hypotheses
strategies_str="${STRATEGIES:-a b c}"
read -r -a strategies <<< "$strategies_str"
hypotheses_str="${HYPOTHESES:-h1_none h2_embed h3_tie_aj h4_tie_wa h5_embed_tie_aj h6_embed_tie_wa h7_tie_wa_tie_aj h8_all}"
read -r -a hypotheses <<< "$hypotheses_str"

for s in "${strategies[@]}"; do
  for h in "${hypotheses[@]}"; do
    in_base="retrofit_${s}.inp"
    in_var="retrofit_${s}_${h}.inp"
    job="retrofit_${s}_${h}"

    echo "Patching ${in_base} -> ${in_var} (${h})"
    python3 abaqus_hypothesis_patcher.py --input "$in_base" --output "$in_var" --force-n "$FORCE_N" --hypothesis "$h"

    echo "Running ${job}"
    abaqus interactive job="$job" input="$in_var" cpus=1 ask_delete=OFF > "${job}_launch.log" 2>&1 || true
  done
done

echo "Sweep complete"
