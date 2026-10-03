"""Turn Jev's answers into matter-level warnings. All arithmetic lives here, not in the model."""

# Thresholds live in code so the matter team can tune them.
CONFIDENT = 0.55      # below this, a Choice answer goes to a person
FLAG_YES = 0.70       # Noul value above which a narrative flag is raised
AMBER_GAP = 10        # budget burned minus work completed, in percentage points
RED_GAP = 25
PRICE_PER_MTOK = 0.042  # Jev 1.13 input price, USD per million tokens


def classify_request(req, ans, eng):
    scope = ans["scope"]
    ws = ans["workstream"]
    names = {w["id"]: w["name"] for w in eng["workstreams"]}
    if scope["confidence"] < CONFIDENT or scope["choice"] == "unclear":
        action, severity = "Partner to decide before any work starts", "review"
    elif scope["choice"] == "out_of_scope":
        action, severity = "Outside the agreed scope: raise with the client and agree a fee before starting", "high"
    else:
        action, severity = f"Proceed under {names.get(ws['choice'], 'the agreed scope')}", "ok"
    return {
        "id": req["id"], "date": req["date"], "from": req["from"], "subject": req["subject"], "body": req["body"],
        "scope": scope["choice"], "scope_confidence": scope["confidence"], "scope_probabilities": scope.get("probabilities", {}),
        "workstream": ws["choice"], "workstream_confidence": ws["confidence"],
        "action": action, "severity": severity, "label": req.get("label"),
    }


def classify_entry(entry, ans, eng):
    rate = eng["rates"][entry["role"]]
    fees = round(entry["hours"] * rate, 2)
    ws = ans["workstream"]
    vague = ans["vague"]["noul"]
    block = ans["block"]["noul"]
    issues = []
    needs_review = ws["confidence"] < CONFIDENT or ws["choice"] == "unclear"
    if ws["choice"] == "out_of_scope" and not needs_review:
        issues.append("Time on excluded work: agree a fee with the client or write it off")
    if vague > FLAG_YES:
        issues.append("Narrative too vague to bill: rewrite before the invoice")
    if block > FLAG_YES:
        issues.append("Several tasks in one entry: split before billing")
    if needs_review:
        issues.append("Workstream unclear: matter manager to confirm")
    return {
        "id": entry["id"], "date": entry["date"], "timekeeper": entry["timekeeper"], "role": entry["role"],
        "hours": entry["hours"], "fees": fees, "narrative": entry["narrative"],
        "workstream": ws["choice"], "workstream_confidence": ws["confidence"],
        "vague": vague, "block": block, "needs_review": needs_review, "issues": issues,
        "label_workstream": entry.get("label_workstream"), "label_flag": entry.get("label_flag"),
    }


def rollup(eng, entries):
    out = []
    for w in eng["workstreams"]:
        mine = [e for e in entries if e["workstream"] == w["id"]]
        period = sum(e["fees"] for e in mine)
        unconfirmed = sum(e["fees"] for e in mine if e["needs_review"])
        spent = w["billed_before_period"] + period
        burn = 100 * spent / w["budget_fees"]
        done = w["pct_complete"]
        gap = burn - done
        projected = spent / (done / 100) if done else None
        if gap > RED_GAP or (burn >= 90 and done < 90):
            rag = "red"
        elif gap > AMBER_GAP or (projected and projected > 1.1 * w["budget_fees"]):
            rag = "amber"
        else:
            rag = "green"
        out.append({
            "id": w["id"], "name": w["name"], "budget": w["budget_fees"], "spent": round(spent, 2),
            "period_fees": round(period, 2), "unconfirmed_fees": round(unconfirmed, 2),
            "burn_pct": round(burn, 1), "pct_complete": done, "gap": round(gap, 1),
            "projected": round(projected, 2) if projected else None, "rag": rag,
        })
    return out


def build_flags(workstreams, requests, entries):
    flags = []
    for w in workstreams:
        if w["rag"] in ("red", "amber"):
            proj = f"; at this pace it finishes near ${w['projected']:,.0f} against a ${w['budget']:,.0f} budget" if w["projected"] else ""
            flags.append({
                "severity": w["rag"],
                "title": f"{w['name']}: {w['burn_pct']:.0f}% of budget spent, {w['pct_complete']}% of the work done",
                "detail": f"Spent ${w['spent']:,.0f} of ${w['budget']:,.0f}{proj}. Talk to the client about the budget before the next invoice.",
            })
    oos_req = [r for r in requests if r["severity"] == "high"]
    if oos_req:
        flags.append({
            "severity": "red",
            "title": f"{len(oos_req)} client requests fall outside the agreed scope",
            "detail": "; ".join(f"{r['subject']} ({r['date']})" for r in oos_req) + ". Agree scope and fees before doing the work.",
        })
    oos_time = [e for e in entries if e["workstream"] == "out_of_scope" and not e["needs_review"]]
    if oos_time:
        fees = sum(e["fees"] for e in oos_time)
        flags.append({
            "severity": "amber",
            "title": f"${fees:,.0f} of time already recorded on excluded work",
            "detail": "; ".join(f"{e['narrative'][:70]} ({e['hours']}h)" for e in oos_time) + ". Bill it under an agreed variation or write it off.",
        })
    fix = [e for e in entries if e["vague"] > FLAG_YES or e["block"] > FLAG_YES]
    if fix:
        flags.append({
            "severity": "amber",
            "title": f"{len(fix)} time entries need rewriting before billing",
            "detail": "Vague or block-billed narratives breach the billing guidelines and invite write-downs.",
        })
    review_r = [r for r in requests if r["severity"] == "review"]
    review_e = [e for e in entries if e["needs_review"]]
    if review_r or review_e:
        flags.append({
            "severity": "review",
            "title": f"{len(review_r) + len(review_e)} items where the model was not confident enough to decide",
            "detail": f"{len(review_r)} requests and {len(review_e)} time entries are waiting for a person. Nothing below the confidence line is decided automatically.",
        })
    order = {"red": 0, "amber": 1, "review": 2}
    return sorted(flags, key=lambda f: order.get(f["severity"], 3))


def evaluate(requests, entries):
    """Compare decisions with the hand labels in the test data."""
    auto_r = [r for r in requests if r["severity"] != "review"]
    req_correct = sum(1 for r in auto_r if r["scope"] == r["label"]["scope"])
    true_unclear = [r for r in requests if r["label"]["scope"] == "unclear"]
    unclear_caught = sum(1 for r in true_unclear if r["severity"] == "review")

    labelled = [e for e in entries if e["label_workstream"] != "unclear"]
    auto_e = [e for e in labelled if not e["needs_review"]]
    ws_correct = sum(1 for e in auto_e if e["workstream"] == e["label_workstream"])

    def pr(flag_name, key):
        pred = {e["id"] for e in entries if e[key] > FLAG_YES}
        truth = {e["id"] for e in entries if e["label_flag"] == flag_name}
        tp = len(pred & truth)
        return {"flagged": len(pred), "true": len(truth), "caught": tp,
                "precision": round(tp / len(pred), 2) if pred else None,
                "recall": round(tp / len(truth), 2) if truth else None}

    return {
        "requests": {"total": len(requests), "decided_automatically": len(auto_r), "correct": req_correct,
                     "accuracy": round(req_correct / len(auto_r), 2) if auto_r else None,
                     "ambiguous_in_test_set": len(true_unclear), "ambiguous_sent_to_review": unclear_caught},
        "time_entries": {"total": len(entries), "sent_to_review": sum(1 for e in entries if e["needs_review"]),
                         "labelled_clear": len(labelled), "decided_automatically": len(auto_e), "correct": ws_correct,
                         "accuracy": round(ws_correct / len(auto_e), 2) if auto_e else None},
        "vague_narratives": pr("vague", "vague"),
        "block_billing": pr("block", "block"),
    }
