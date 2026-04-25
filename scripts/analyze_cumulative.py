"""Анализ кумулятивного эффекта памяти: как action_count снижается по мере накопления site graph."""
import json
import sys
from pathlib import Path


def analyze(results_path: str) -> None:
    data = json.loads(Path(results_path).read_text())
    cases = data.get("cases", [])

    print(f"{'#':<4} {'case_id':<14} {'baseline':>9} {'memory':>7} {'delta':>7} {'reduction':>10} {'quality':<10}")
    print("-" * 70)

    reductions = []
    for i, c in enumerate(cases, 1):
        if "error" in c:
            print(f"{i:<4} {c['case_id']:<14} {'ERROR':>9}")
            continue
        b = c.get("baseline_actions", 0)
        m = c.get("memory_actions", 0)
        d = c.get("action_delta", 0)
        pct = d / b * 100 if b > 0 else 0
        mem = "✓" if c.get("memory_used") else "✗"
        b_ok = "✓" if c.get("baseline_status") == "succeeded" else "✗"
        m_ok = "✓" if c.get("memory_status") == "succeeded" else "✗"
        reductions.append(pct)
        print(f"{i:<4} {c['case_id']:<14} {b:>7}{b_ok}  {m:>5}{m_ok}  {d:>+6}  {pct:>+8.1f}%  mem={mem}")

    print("-" * 70)
    if reductions:
        print(f"\nТренд (скользящее среднее по 3):")
        for i in range(len(reductions)):
            window = reductions[max(0, i-2):i+1]
            avg = sum(window) / len(window)
            bar = "█" * max(0, int(avg / 5)) if avg > 0 else "░" * max(0, int(-avg / 5))
            sign = "+" if avg >= 0 else ""
            print(f"  Задача {i+1:>2}: {sign}{avg:>6.1f}%  {bar}")

        print(f"\nИтог:")
        print(f"  Первые 3 задачи:  avg {sum(reductions[:3])/3:+.1f}%")
        print(f"  Последние 3:      avg {sum(reductions[-3:])/3:+.1f}%")
        print(f"  Все:              avg {sum(reductions)/len(reductions):+.1f}%")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "results/eval_kinostar.json"
    analyze(path)
