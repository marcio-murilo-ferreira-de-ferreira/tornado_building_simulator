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
python3 prepare_additional_sensitivity_cases.py

for py in sensitivity_run_d_*.py sensitivity_run_e_*.py sensitivity_run_f_*.py sensitivity_run_g_*.py sensitivity_run_h_*.py; do
  base="${py%.py}"
  key="${base#sensitivity_run_}"   # d_case ... h_case
  job="sens_${key}"
  echo "Generating INP for ${job}"
  abaqus cae noGUI="$py" > "gen_${job}.log" 2>&1 || true
  if [[ ! -f "${job}.inp" ]]; then
    echo "Missing ${job}.inp; skipping"
    continue
  fi

  patched="${job}_h5.inp"
  runjob="${job}_h5"
  if ! python3 abaqus_hypothesis_patcher.py --input "${job}.inp" --output "$patched" --force-n "$FORCE_N" --hypothesis h5_embed_tie_aj; then
    echo "Hypothesis patch failed for ${job}; falling back to unpatched input."
    cp "${job}.inp" "$patched"
  fi

  echo "Running ${runjob}"
  abaqus interactive job="$runjob" input="$patched" cpus=1 ask_delete=OFF > "${runjob}_launch.log" 2>&1 || true
done

echo "Extracting sensitivity results -> bc_sensitivity_results.json"
abaqus python abaqus_sweep_extract.py --pattern "sens_*_h5" --out bc_sensitivity_results.json || true

echo "Additional sensitivity complete"
