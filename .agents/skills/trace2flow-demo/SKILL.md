---
name: trace2flow-demo
description: Use when running a live Codex CLI demonstration of trace2flow, or when the user asks to show baseline vs optimize vs memory-run with real metrics
---

# Trace2flow Demo

Run a live end-to-end demonstration of the `trace2flow` workflow-memory loop from Codex.

Use the validated MAI schedule scenario, not `books.toscrape.com`. The books demo can succeed without making the memory benefit visually obvious. The MAI scenario has a recorded best-case improvement in the repo artifacts and is the preferred live-demo path.

## Invocation

- Trigger with `$trace2flow-demo`
- Optional args: `full`, `baseline`, `results`, `--fresh`
- If no args are given, treat the mode as `full`
- Treat all text after `$trace2flow-demo` as mode arguments

Example:

```text
$trace2flow-demo
$trace2flow-demo baseline --fresh
$trace2flow-demo results
```

## Codex Notes

- Run commands from `/Users/a/MAI/sem2/trace2flow`
- Use the terminal execution tool (`functions.exec_command` or the session shell tool) for all commands
- Use file reads only when you need to inspect or summarize saved outputs
- Keep the user updated between major demo stages
- For live demos, prefer `--no-headless` so the browser is visible
- If `OPENROUTER_API_KEY` is missing, stop and tell the user to export it before retrying

## Constants

- Project root: `/Users/a/MAI/sem2/trace2flow`
- Demo task: `Зайди на https://mai.ru/education/studies/schedule/groups.php и найди расписание группы М8О-108БВ-25 (8 институт, 1 курс, базовое высшее) на среду 30.04`
- Demo site: `mai.ru`
- Database: `data/workflow_memory.sqlite`
- Expected improvement: about `20 -> 3` actions, roughly `85%` fewer actions
- Evidence source: `results/eval_20_combined.json`, case `mai-s05`

## Modes

- `full`: run the complete cycle: baseline -> optimize -> memory-run -> comparison
- `baseline`: run only the blind baseline and show the result
- `results`: show the validated MAI evaluation summary from `results/`
- `--fresh`: clear stored memory for the demo site before running

## Timing Banner

Before `full` mode, tell the user:

```text
Estimated real time:
- Baseline run: 3-8 min
- Optimize: 30-60 sec
- Memory-run: 1-4 min
- Total: 5-13 min
```

## Step 1: Environment Check

Run:

```bash
cd /Users/a/MAI/sem2/trace2flow
source .venv/bin/activate
echo "CLI: $(workflow-memory --version 2>/dev/null || echo 'workflow-memory installed')"
echo "API key: ${OPENROUTER_API_KEY:+set}${OPENROUTER_API_KEY:-MISSING}"
echo "DB: $([ -f data/workflow_memory.sqlite ] && echo exists || echo 'will be created')"
python3 -m playwright install chromium --dry-run 2>&1 | grep -i "chromium" | head -1 || echo "Playwright: ready"
```

If the API key is missing, stop.

## Step 2: Fresh Start

For `full` and `baseline`, clear existing memory for the demo site before the run. Also do this when `--fresh` is explicitly passed.

```bash
cd /Users/a/MAI/sem2/trace2flow
python3 -c "
import os, sqlite3
db_path = 'data/workflow_memory.sqlite'
if not os.path.exists(db_path):
    print('DB not yet created - baseline will be the first run')
else:
    db = sqlite3.connect(db_path)
    deleted = db.execute(\"DELETE FROM memories WHERE site = 'mai.ru'\").rowcount
    db.commit()
    db.close()
    print(f'Cleared {deleted} memory entries for mai.ru')
    print('Agent will run blind - no prior knowledge')
"
```

Report what was cleared.

## Step 3: Baseline Run

Announce:

```text
Step 1/3 - Baseline run on MAI (agent explores the schedule flow from scratch)
```

Run:

```bash
cd /Users/a/MAI/sem2/trace2flow
source .venv/bin/activate
TASK="Зайди на https://mai.ru/education/studies/schedule/groups.php и найди расписание группы М8О-108БВ-25 (8 институт, 1 курс, базовое высшее) на среду 30.04"
echo "Task: $TASK"
echo "Starting baseline... (browser will open)"
workflow-memory run --task "$TASK" --output --no-headless 2>/tmp/t2f_run_stderr.txt | tee /tmp/t2f_baseline.json
```

Then parse:

```bash
python3 -c "
import json
with open('/tmp/t2f_baseline.json') as f:
    r = json.load(f)
print()
print('BASELINE RESULT')
print(f'Status: {r[\"status\"]}')
print(f'Actions taken: {r[\"action_count\"]}')
print(f'Time elapsed: {r[\"elapsed_seconds\"]:.0f}s ({r[\"elapsed_seconds\"]/60:.1f} min)')
print(f'Run ID: {r[\"run_id\"]}')
with open('/tmp/t2f_run_id.txt', 'w') as f:
    f.write(r['run_id'])
with open('/tmp/t2f_baseline_count.txt', 'w') as f:
    f.write(str(r['action_count']))
with open('/tmp/t2f_baseline_time.txt', 'w') as f:
    f.write(str(r['elapsed_seconds']))
"
```

If the baseline did not succeed, stop and report the failure.

## Step 4: Optimize

Announce:

```text
Step 2/3 - Analyzing the MAI run and storing workflow memory
```

Run:

```bash
cd /Users/a/MAI/sem2/trace2flow
source .venv/bin/activate
RUN_ID=$(cat /tmp/t2f_run_id.txt)
echo "Optimizing run $RUN_ID..."
workflow-memory optimize --run-id "$RUN_ID" 2>&1 | tee /tmp/t2f_optimize.txt
```

Then inspect what was stored:

```bash
python3 -c "
import json, sqlite3
db = sqlite3.connect('data/workflow_memory.sqlite')
db.row_factory = sqlite3.Row
row = db.execute(
    \"SELECT * FROM memories WHERE site = 'mai.ru' ORDER BY admitted_at DESC LIMIT 1\"
).fetchone()
if row is None:
    print('Memory was not admitted - check /tmp/t2f_optimize.txt')
else:
    packet = json.loads(row['hint_packet_json'])
    print()
    print('WHAT THE AGENT LEARNED')
    if packet.get('direct_url'):
        print(f'Direct URL: {packet[\"direct_url\"]}')
    hints = packet.get('page_hints', [])
    if hints:
        print(f'Page hints ({len(hints)}):')
        for hint in hints[:3]:
            print(f'- {hint[:80]}')
    cues = packet.get('success_cues', [])
    if cues:
        print(f'Success cue: {cues[0][:60]}')
    print(f'Memory ID: {row[\"memory_id\"]}')
"
```

## Step 5: Memory-Run

Announce:

```text
Step 3/3 - Memory-run on MAI (agent uses stored direct URL and site knowledge)
```

Run:

```bash
cd /Users/a/MAI/sem2/trace2flow
source .venv/bin/activate
TASK="Зайди на https://mai.ru/education/studies/schedule/groups.php и найди расписание группы М8О-108БВ-25 (8 институт, 1 курс, базовое высшее) на среду 30.04"
echo "Same task, memory-augmented prompt..."
workflow-memory memory-run --task "$TASK" --output --no-headless 2>/tmp/t2f_memrun_stderr.txt | tee /tmp/t2f_memrun.json
```

Then parse:

```bash
python3 -c "
import json
with open('/tmp/t2f_memrun.json') as f:
    r = json.load(f)
print()
print('MEMORY-RUN RESULT')
print(f'Status: {r[\"status\"]}')
print(f'Actions taken: {r[\"action_count\"]}')
print(f'Time elapsed: {r[\"elapsed_seconds\"]:.0f}s ({r[\"elapsed_seconds\"]/60:.1f} min)')
print(f'Memory used: {r.get(\"memory_used\", \"?\")}')
with open('/tmp/t2f_memrun_count.txt', 'w') as f:
    f.write(str(r['action_count']))
with open('/tmp/t2f_memrun_time.txt', 'w') as f:
    f.write(str(r['elapsed_seconds']))
"
```

## Step 6: Comparison Table

Run:

```bash
python3 -c "
baseline = int(open('/tmp/t2f_baseline_count.txt').read())
memory = int(open('/tmp/t2f_memrun_count.txt').read())
t_base = float(open('/tmp/t2f_baseline_time.txt').read())
t_mem = float(open('/tmp/t2f_memrun_time.txt').read())
saved = baseline - memory
pct = saved / baseline * 100 if baseline else 0
t_saved = t_base - t_mem
print()
print('TRACE2FLOW DEMO - RESULTS')
print('Scenario: mai.ru schedule lookup (validated mai-s05 case)')
print(f'Baseline: {baseline} actions, {t_base:.0f}s')
print(f'Memory:   {memory} actions, {t_mem:.0f}s')
print(f'Actions saved: {saved:+d} ({pct:.0f}% fewer)')
print(f'Time saved: {t_saved:.0f}s')
if pct > 0:
    print(f'Hypothesis confirmed: memory reduced actions by {pct:.0f}%')
else:
    print('No improvement this run - inspect optimize output')
"
```

## Results Mode

If the mode is `results`, summarize the validated MAI result set first. Do not pick an arbitrary latest file.

```bash
cd /Users/a/MAI/sem2/trace2flow
python3 - <<'EOF'
import json, os

combined_path = 'results/eval_20_combined.json'
mai_path = 'results/eval_mai.json'

if os.path.exists(combined_path):
    with open(combined_path) as f:
        combined = json.load(f)
    mai = next((item for item in combined if item.get('suite') == 'mai'), None)
    if mai:
        print(f"Source: {combined_path}")
        print(f"Suite: mai")
        print(f"Cases: {mai['total_cases']}")
        print(f"Baseline success: {mai['baseline_success_rate']:.0%}")
        print(f"Memory success: {mai['memory_success_rate']:.0%}")
        print(f"Average action reduction: {mai['avg_action_reduction_pct']:.1f}%")
        best = max(mai['cases'], key=lambda item: item.get('action_delta', -999))
        print(
            f"Best case: {best['case_id']} | "
            f"{best['baseline_actions']} -> {best['memory_actions']} actions | "
            f"delta +{best['action_delta']}"
        )
        print(f"Best task: {best['task']}")
        raise SystemExit(0)

if os.path.exists(mai_path):
    with open(mai_path) as f:
        mai = json.load(f)
    print(f"Source: {mai_path}")
    print(json.dumps(mai, ensure_ascii=False, indent=2))
else:
    print('No MAI eval results found')
EOF
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `OPENROUTER_API_KEY` missing | `export OPENROUTER_API_KEY=sk-or-...` |
| `workflow-memory: command not found` | `source .venv/bin/activate` |
| Browser launch failure | `python -m playwright install chromium` |
| Optimize says not admitted | Repeat baseline and optimize |
| `memory_used: False` | Check `/tmp/t2f_optimize.txt` |
| Demo shows weak improvement | Use the exact validated MAI task from `mai-s05`, not a paraphrase |
