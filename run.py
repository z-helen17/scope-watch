"""Scope Watch: early warnings on scope and budget for a law firm matter, powered by Jev.

Usage:
    python run.py            # live, needs TYPESAFE_API_KEY (in .env or the environment)
    python run.py --mock     # offline, invented answers, for building and layout only
"""
import argparse
import json
import os
from datetime import datetime
from pathlib import Path

from scope_watch import analyse, dashboard
from scope_watch.data import load_engagement, load_requests, load_timesheets
from scope_watch.jev_client import JevClient
from scope_watch.questions import request_questions, time_entry_questions

ROOT = Path(__file__).resolve().parent


def load_env():
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true", help="run offline with invented answers")
    ap.add_argument("--model", default="jev-latest")
    ap.add_argument("--out", default=str(ROOT / "output"))
    args = ap.parse_args()

    load_env()
    eng, reqs, entries = load_engagement(), load_requests(), load_timesheets()
    jev = JevClient(mock=args.mock, model=args.model)

    rq = request_questions(eng)
    tq = time_entry_questions(eng)

    req_results = []
    for r in reqs:
        lab = r.get("label", {})
        hints = {"scope": lab.get("scope"), "scope_hard": lab.get("scope") == "unclear",
                 "workstream": lab.get("workstream") or "none"}
        ans = jev.ask(r["id"], {"subject": r["subject"], "message": r["body"]}, rq, hints)
        req_results.append(analyse.classify_request(r, ans, eng))

    entry_results = []
    for e in entries:
        hints = {"workstream": e["label_workstream"], "workstream_hard": e["label_workstream"] == "unclear",
                 "vague": e["label_flag"] == "vague", "block": e["label_flag"] == "block"}
        ans = jev.ask(e["id"], {"narrative": e["narrative"], "timekeeper_role": e["role"]}, tq, hints)
        entry_results.append(analyse.classify_entry(e, ans, eng))
    jev.close()

    workstreams = analyse.rollup(eng, entry_results)
    flags = analyse.build_flags(workstreams, req_results, entry_results)
    evaluation = analyse.evaluate(req_results, entry_results)

    results = {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "mode": "mock" if args.mock else "live",
        "model": jev.model_used,
        "calls": jev.calls,
        "input_tokens": jev.input_tokens,
        "cost_usd": round(jev.input_tokens / 1e6 * analyse.PRICE_PER_MTOK, 5),
        "thresholds": {"confident": analyse.CONFIDENT, "flag_yes": analyse.FLAG_YES,
                       "amber_gap": analyse.AMBER_GAP, "red_gap": analyse.RED_GAP},
        "matter": eng["matter"],
        "workstreams": workstreams,
        "flags": flags,
        "requests": req_results,
        "entries": entry_results,
        "evaluation": evaluation,
    }
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (out / "dashboard.html").write_text(dashboard.render(results), encoding="utf-8")
    print(f"{results['mode']} run: {jev.calls} Jev calls, {jev.input_tokens} input tokens, ${results['cost_usd']}")
    print(f"Dashboard: {out / 'dashboard.html'}")
    ev = evaluation
    print(f"Requests decided automatically: {ev['requests']['decided_automatically']}/{ev['requests']['total']}, "
          f"accuracy {ev['requests']['accuracy']}; ambiguous sent to review {ev['requests']['ambiguous_sent_to_review']}/{ev['requests']['ambiguous_in_test_set']}")
    print(f"Time entries sent to review: {ev['time_entries']['sent_to_review']}/{ev['time_entries']['total']}; "
          f"workstream accuracy on the rest {ev['time_entries']['accuracy']}")


if __name__ == "__main__":
    main()
