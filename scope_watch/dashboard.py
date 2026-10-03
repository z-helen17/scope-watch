"""Render results.json as a single self-contained HTML dashboard."""
from html import escape

CSS = """
:root{color-scheme:light;--ink:#1d2330;--muted:#5d6675;--line:#e4e7ee;--soft:#f5f7fb;--navy:#1f2f4f;
--red:#c0392b;--redbg:#fdecea;--amber:#b7791f;--amberbg:#fff6e0;--green:#2f7a4f;--greenbg:#e8f5ee;--rev:#5b4bb7;--revbg:#efedfb}
*{box-sizing:border-box}body{margin:0;font-family:"Segoe UI",-apple-system,Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:#f0f2f6;font-size:14px;line-height:1.45}
.wrap{max-width:1180px;margin:0 auto;padding:22px}
header{background:var(--navy);color:#fff;border-radius:14px;padding:20px 24px;display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}
header h1{margin:0 0 4px;font-size:20px}header .sub{color:#cdd6e6;font-size:13px}
.badge{display:inline-block;border-radius:20px;padding:3px 10px;font-size:12px;font-weight:700}
.mock{background:#ffcf8a;color:#5a3b00}.live{background:#9fe0bc;color:#0d4a2b}
h2{font-size:15px;margin:26px 0 10px;color:var(--navy)}
.grid{display:grid;gap:12px}.g4{grid-template-columns:repeat(auto-fit,minmax(250px,1fr))}
.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.flag{border-left:5px solid var(--line)}.flag.red{border-left-color:var(--red)}.flag.amber{border-left-color:var(--amber)}.flag.review{border-left-color:var(--rev)}
.flag b{display:block;margin-bottom:3px}.flag p{margin:0;color:var(--muted);font-size:13px}
.pill{display:inline-block;border-radius:10px;padding:1px 8px;font-size:11.5px;font-weight:700;text-transform:uppercase;letter-spacing:.03em}
.pill.red{background:var(--redbg);color:var(--red)}.pill.amber{background:var(--amberbg);color:var(--amber)}.pill.green{background:var(--greenbg);color:var(--green)}
.pill.review{background:var(--revbg);color:var(--rev)}.pill.ok{background:var(--greenbg);color:var(--green)}.pill.high{background:var(--redbg);color:var(--red)}
.ws h3{margin:0 0 8px;font-size:14px;display:flex;justify-content:space-between;gap:8px}
.bar{position:relative;height:12px;background:#eef1f6;border-radius:6px;overflow:visible;margin:10px 0 6px}
.fill{height:100%;border-radius:6px}.fill.red{background:var(--red)}.fill.amber{background:var(--amber)}.fill.green{background:var(--green)}
.mark{position:absolute;top:-4px;width:2px;height:20px;background:var(--navy)}
.ws .nums{display:flex;justify-content:space-between;color:var(--muted);font-size:12.5px}
.ws .proj{margin-top:6px;font-size:12.5px}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top;font-size:13px}
th{background:var(--soft);font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.03em}
td.msg{max-width:360px;color:var(--muted)}
.conf{display:inline-block;width:60px;height:6px;background:#eef1f6;border-radius:3px;vertical-align:middle;margin-left:6px}
.conf i{display:block;height:100%;border-radius:3px;background:var(--navy)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
.kpi b{display:block;font-size:22px;color:var(--navy)}.kpi span{color:var(--muted);font-size:12.5px}
.how{font-size:13px;color:var(--muted)}.how li{margin-bottom:4px}
footer{margin:26px 0 10px;color:var(--muted);font-size:12px}
.note{background:var(--amberbg);border:1px solid #f0d9a0;border-radius:10px;padding:10px 14px;margin-top:12px;font-size:13px}
"""

WS_NAMES = {}


def _conf(v):
    pct = max(0, min(100, round(v * 100)))
    return f'{v:.2f}<span class="conf"><i style="width:{pct}%"></i></span>'


def _ws_name(i):
    return WS_NAMES.get(i, {"out_of_scope": "Out of scope", "unclear": "Unclear", "none": "None"}.get(i, i))


def render(res):
    WS_NAMES.clear()
    WS_NAMES.update({w["id"]: w["name"] for w in res["workstreams"]})
    m = res["matter"]
    mode = res["mode"]
    h = []
    h.append(f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><title>Scope Watch: {escape(m['name'])}</title><style>{CSS}</style></head><body><div class='wrap'>")
    badge = "<span class='badge mock'>MOCK DATA: answers invented offline</span>" if mode == "mock" else f"<span class='badge live'>LIVE: {escape(str(res['model']))}</span>"
    h.append(f"<header><div><h1>Scope Watch</h1><div class='sub'>{escape(m['name'])}<br>{escape(m['firm_role'])} · Client: {escape(m['client'])} · As of {escape(m['as_of'])}</div></div><div>{badge}</div></header>")
    if mode == "mock":
        h.append("<div class='note'>This run used invented answers so the layout can be checked without an API key. Run <code>python run.py</code> with a TypeSafe key for real Jev answers and real accuracy figures.</div>")

    # KPIs
    budget = sum(w["budget"] for w in res["workstreams"])
    spent = sum(w["spent"] for w in res["workstreams"])
    oos = sum(1 for r in res["requests"] if r["severity"] == "high")
    fixes = sum(1 for e in res["entries"] if e["vague"] > res["thresholds"]["flag_yes"] or e["block"] > res["thresholds"]["flag_yes"])
    review = sum(1 for r in res["requests"] if r["severity"] == "review") + sum(1 for e in res["entries"] if e["needs_review"])
    h.append("<h2>At a glance</h2><div class='kpis'>")
    for val, lab in [(f"${spent:,.0f}", f"spent of ${budget:,.0f} total budget"), (str(oos), "client requests outside the agreed scope"),
                     (str(fixes), "time entries to rewrite before billing"), (str(review), "items waiting for a person")]:
        h.append(f"<div class='card kpi'><b>{val}</b><span>{lab}</span></div>")
    h.append("</div>")

    # Flags
    h.append("<h2>Early warnings</h2><div class='grid'>")
    if not res["flags"]:
        h.append("<div class='card'>No warnings.</div>")
    for f in res["flags"]:
        h.append(f"<div class='card flag {f['severity']}'><b><span class='pill {f['severity']}'>{f['severity']}</span> {escape(f['title'])}</b><p>{escape(f['detail'])}</p></div>")
    h.append("</div>")

    # Workstreams
    h.append("<h2>Budget by workstream</h2><div class='grid g4'>")
    for w in res["workstreams"]:
        width = min(100, w["burn_pct"])
        proj = f"Projected at completion: <b>${w['projected']:,.0f}</b>" if w["projected"] else ""
        unconf = f"<div class='nums'><span>${w['unconfirmed_fees']:,.0f} of this period's time not yet confirmed</span></div>" if w["unconfirmed_fees"] else ""
        h.append(f"<div class='card ws'><h3>{escape(w['name'])}<span class='pill {w['rag']}'>{w['rag']}</span></h3>"
                 f"<div class='bar'><div class='fill {w['rag']}' style='width:{width}%'></div><div class='mark' style='left:{w['pct_complete']}%' title='Work complete'></div></div>"
                 f"<div class='nums'><span>{w['burn_pct']:.0f}% of budget spent</span><span>{w['pct_complete']}% done (marker)</span></div>"
                 f"<div class='nums'><span>${w['spent']:,.0f} / ${w['budget']:,.0f}</span></div>{unconf}<div class='proj'>{proj}</div></div>")
    h.append("</div>")

    # Requests
    h.append("<h2>Client requests</h2><table><tr><th>Date</th><th>Request</th><th>Jev: scope</th><th>Workstream</th><th>Action</th></tr>")
    for r in sorted(res["requests"], key=lambda x: x["date"], reverse=True):
        h.append(f"<tr><td>{escape(r['date'])}</td><td><b>{escape(r['subject'])}</b><br><span class='msg'>{escape(r['body'])}</span></td>"
                 f"<td>{escape(r['scope'].replace('_', ' '))}<br>{_conf(r['scope_confidence'])}</td>"
                 f"<td>{escape(_ws_name(r['workstream']))}</td><td><span class='pill {r['severity']}'>{'review' if r['severity']=='review' else ('out of scope' if r['severity']=='high' else 'ok')}</span><br>{escape(r['action'])}</td></tr>")
    h.append("</table>")

    # Entries needing attention
    attn = [e for e in res["entries"] if e["issues"]]
    h.append(f"<h2>Time entries needing attention ({len(attn)} of {len(res['entries'])})</h2><table><tr><th>Date</th><th>Timekeeper</th><th>Hours</th><th>Narrative</th><th>Jev: workstream</th><th>What to do</th></tr>")
    for e in attn:
        h.append(f"<tr><td>{escape(e['date'])}</td><td>{escape(e['timekeeper'])}<br><span class='msg'>{escape(e['role'])}</span></td><td>{e['hours']}</td>"
                 f"<td class='msg'>{escape(e['narrative'])}</td><td>{escape(_ws_name(e['workstream']))}<br>{_conf(e['workstream_confidence'])}</td>"
                 f"<td>{'<br>'.join(escape(i) for i in e['issues'])}</td></tr>")
    h.append("</table>")

    # How it works
    t = res["thresholds"]
    h.append("<h2>How it decides</h2><div class='card how'><ul>"
             "<li><b>Jev makes the narrow judgments:</b> whether each client request is inside the agreed scope, excluded, or unclear; which workstream each time entry belongs to; whether a narrative is too vague to bill or combines several tasks.</li>"
             "<li><b>Code does the arithmetic:</b> fees from hours and rates, budget burned against work completed, projected cost at completion, and the warnings.</li>"
             f"<li><b>Uncertainty goes to a person:</b> any answer with confidence below {t['confident']} is never acted on automatically; it lands in the review queue with the model's probabilities, so the partner sees why.</li>"
             f"<li><b>Warning levels:</b> amber when budget burned runs more than {t['amber_gap']} points ahead of work completed (or the projection exceeds budget by 10%); red above {t['red_gap']} points, or 90% spent on unfinished work.</li>"
             "</ul></div>")

    # Evaluation
    ev = res["evaluation"]
    note = " (mock run: these figures mean nothing until the live run)" if mode == "mock" else ""
    h.append(f"<h2>Accuracy on the labelled test set{note}</h2><div class='kpis'>")
    rq, te = ev["requests"], ev["time_entries"]
    vb, bb = ev["vague_narratives"], ev["block_billing"]
    cards = [
        (f"{rq['correct']}/{rq['decided_automatically']}", f"requests decided automatically and correctly ({rq['total']} total)"),
        (f"{rq['ambiguous_sent_to_review']}/{rq['ambiguous_in_test_set']}", "genuinely ambiguous requests sent to a person"),
        (f"{te['correct']}/{te['decided_automatically']}", "clear time entries tagged to the right workstream"),
        (f"{te['sent_to_review']}/{te['total']}", "time entries sent for review"),
        (f"{vb['caught']}/{vb['true']}", f"vague narratives caught ({vb['flagged']} flagged)"),
        (f"{bb['caught']}/{bb['true']}", f"block-billed entries caught ({bb['flagged']} flagged)"),
    ]
    for val, lab in cards:
        h.append(f"<div class='card kpi'><b>{val}</b><span>{escape(lab)}</span></div>")
    h.append("</div>")

    h.append(f"<footer>Generated {escape(res['generated'])} · {res['calls']} Jev calls · {res['input_tokens']:,} input tokens · approx ${res['cost_usd']} · "
             f"{escape(m.get('note', ''))}</footer></div></body></html>")
    return "".join(h)
