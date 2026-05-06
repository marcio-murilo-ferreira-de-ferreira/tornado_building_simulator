#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ABAQUS_CMD="${ABAQUS_CMD:-abaqus}"
RUN_ABAQUS=1

usage() {
  cat <<'EOF'
Usage: ./run_full_pipeline.sh [--skip-abaqus] [--abaqus-cmd CMD]

Runs the full workflow:
1) optimization
2) generate best-by-strategy Abaqus scripts
3) (optional) run Abaqus jobs for A-H
4) extract Abaqus results
5) export FE snapshots (before/U/Smax)
6) rebuild dashboard

Options:
  --skip-abaqus       Skip Abaqus job execution (uses existing ODBs if present)
  --abaqus-cmd CMD    Abaqus command (default: env ABAQUS_CMD or 'abaqus')
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-abaqus)
      RUN_ABAQUS=0
      shift
      ;;
    --abaqus-cmd)
      ABAQUS_CMD="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

cd "$ROOT"

echo "[1/6] Running optimization..."
python3 forensic_retrofit_optimizer.py

echo "[2/6] Generating best-by-strategy Abaqus scripts..."
python3 generate_abaqus_batch.py

if [[ "$RUN_ABAQUS" -eq 1 ]]; then
  if ! command -v "$ABAQUS_CMD" >/dev/null 2>&1; then
    echo "Abaqus command not found: $ABAQUS_CMD" >&2
    echo "Use --skip-abaqus to build dashboard from existing ODBs/results." >&2
    exit 2
  fi

  echo "[3/6] Running Abaqus jobs (A-H)..."
  for s in A B C D E F G H; do
    script="abaqus_run_${s}.py"
    job="retrofit_${s,,}"
    inp="${job}.inp"
    if [[ ! -f "$script" ]]; then
      echo "Missing script: $script" >&2
      exit 3
    fi
    echo "  - $script"
    "$ABAQUS_CMD" cae "noGUI=$script"
    if [[ ! -f "$inp" ]]; then
      echo "Missing input deck after preprocessing: $inp" >&2
      exit 4
    fi
    rm -f "${job}.lck"
    echo "    solving $job from $inp"
    "$ABAQUS_CMD" "job=$job" "input=$inp" "cpus=1" "ask_delete=OFF"
  done
else
  echo "[3/6] Skipping Abaqus job execution (--skip-abaqus)."
fi

echo "[4/6] Extracting Abaqus metrics..."
if command -v "$ABAQUS_CMD" >/dev/null 2>&1; then
  "$ABAQUS_CMD" python abaqus_extract.py -- \
    retrofit_a retrofit_b retrofit_c retrofit_d retrofit_e retrofit_f retrofit_g retrofit_h \
    abaqus_results.json || true
else
  echo "  - skipped (Abaqus unavailable)"
fi

echo "[5/6] Exporting FE images..."
python3 export_best_strategy_images.py --root "$ROOT" --abaqus-cmd "$ABAQUS_CMD" || true

echo "[6/6] Building dashboard..."
python3 build_dashboard.py

echo "Done. Open: $ROOT/retrofit_dashboard.html"
