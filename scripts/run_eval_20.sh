#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate

RESULTS_DIR="results"
mkdir -p "$RESULTS_DIR"
COMBINED="$RESULTS_DIR/eval_20_combined.json"

echo "[]" > "$COMBINED"

run_suite() {
    local suite="$1"
    local label="$2"
    local out="$RESULTS_DIR/eval_${label}.json"
    local log="$RESULTS_DIR/eval_${label}_log.txt"

    echo ""
    echo "=========================================="
    echo "Suite: $label ($suite)"
    echo "Started: $(date)"
    echo "=========================================="

    workflow-memory eval-batch \
        --suite "$suite" \
        --output \
        --max-steps 20 \
        2>"$log" \
        > "$out" || {
        echo "Suite $label failed (exit $?), continuing..."
        return
    }

    echo "Done: $label  →  $out"

    python3 - <<PYEOF
import json, sys
combined_path = "$COMBINED"
new_path = "$out"
try:
    combined = json.loads(open(combined_path).read())
    new_data = json.loads(open(new_path).read())
    combined.append({"suite": "$label", **new_data})
    open(combined_path, "w").write(json.dumps(combined, indent=2, ensure_ascii=False))
    cases = new_data.get("cases", [])
    ok = [c for c in cases if "error" not in c]
    print(f"  {len(ok)}/{len(cases)} cases ok | avg_delta={new_data.get('avg_action_delta', 0):.1f} | reduction={new_data.get('avg_action_reduction_pct', 0):.0f}%")
except Exception as e:
    print(f"  Merge error: {e}", file=sys.stderr)
PYEOF
}

run_suite "tasks/mai_schedule_eval.yaml"    "mai"
run_suite "tasks/books_toscrape_eval.yaml"  "books"
run_suite "tasks/quotes_toscrape_eval.yaml" "quotes"

echo ""
echo "=========================================="
echo "ALL SUITES COMPLETE  $(date)"
echo "Results: $COMBINED"
echo "=========================================="

python3 - <<PYEOF
import json
data = json.loads(open("$COMBINED").read())
total_cases = sum(s.get("total_cases", 0) for s in data)
avg_reduction = sum(s.get("avg_action_reduction_pct", 0) for s in data) / max(len(data), 1)
print(f"Total cases:       {total_cases}")
print(f"Avg reduction:     {avg_reduction:.0f}%")
for s in data:
    print(f"  {s['suite']:10s}  delta={s.get('avg_action_delta',0):.1f}  reduction={s.get('avg_action_reduction_pct',0):.0f}%  memory_used={s.get('memory_used_count',0)}/{s.get('total_cases',0)}")
PYEOF
