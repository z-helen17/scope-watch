"""Print the accuracy figures from the last run (output/results.json)."""
import json
from pathlib import Path

res = json.loads((Path(__file__).resolve().parent / "output" / "results.json").read_text(encoding="utf-8"))
print(f"Mode: {res['mode']}  Model: {res['model']}  Calls: {res['calls']}  Tokens: {res['input_tokens']}  Cost: ${res['cost_usd']}")
print(json.dumps(res["evaluation"], indent=2))
print("\nRequests sent to review:")
for r in res["requests"]:
    if r["severity"] == "review":
        print(f"  {r['id']} {r['subject']}: {r['scope']} ({r['scope_confidence']:.2f}) | label: {r['label']['scope']}")
print("\nMistakes among automatic decisions:")
for r in res["requests"]:
    if r["severity"] != "review" and r["scope"] != r["label"]["scope"]:
        print(f"  request {r['id']} {r['subject']}: said {r['scope']}, label {r['label']['scope']}")
for e in res["entries"]:
    if not e["needs_review"] and e["label_workstream"] != "unclear" and e["workstream"] != e["label_workstream"]:
        print(f"  entry {e['id']}: said {e['workstream']}, label {e['label_workstream']} | {e['narrative'][:70]}")
