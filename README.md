# Scope Watch

Early warnings on scope and budget for a law firm matter, built on TypeSafe's Jev for the vibecode.law **Build with Jev** challenge.

A matter team gets two kinds of surprise: work the client asks for that was never in the engagement letter, and a phase that quietly burns through its budget before anyone looks. Scope Watch reads the client's requests and the team's time entries against the agreed scope and budget, and raises the flags before the invoice goes out.

**Everything in `data/` is invented.** The matter (lender-side construction and term financing of a 120 MW wind farm in West Texas), the people, the requests and the time entries are fictional test data.

## How it splits the work

| Jev decides (narrow judgments) | Code does (arithmetic and rules) |
|---|---|
| Is this request in scope, excluded, or unclear? | Fees from hours and rates |
| Which workstream does it relate to? | Budget burned against work completed |
| Which workstream does this time entry belong to? | Projected cost at completion |
| Is the narrative too vague to bill? | Red / amber / green per workstream |
| Does it combine several tasks (block billing)? | Which items need a person |

Any answer below the confidence line (0.55, set in `scope_watch/analyse.py`) is never acted on automatically. It goes to the review queue with the model's probabilities.

## Run it

You need Python 3.10 or later.

```
cd scope-watch
py -m venv .venv
.venv\Scripts\activate
pip install -r python-requirements.txt
```

**Offline first (no key needed).** This invents answers from the test labels so you can see the dashboard:

```
python run.py --mock
```

Open `output/dashboard.html` in a browser.

**Live with Jev.** Copy `.env.example` to `.env`, paste your TypeSafe API key after `TYPESAFE_API_KEY=`, then:

```
python run.py
python evaluate.py
```

The live run makes 60 calls (16 requests, 44 time entries). At Jev's price of $0.042 per million input tokens it costs a fraction of a cent. `evaluate.py` prints accuracy against the hand labels and lists every mistake, which is what to tune next.

**Never commit `.env`.** It is already in `.gitignore`.

## Files

- `data/engagement.json` - scope, workstreams, exclusions, budgets, rates, % complete
- `data/requests.json` - 16 client requests, each with the right answer for testing
- `data/timesheets.csv` - 44 time entries with labels (including vague and block-billed ones)
- `scope_watch/questions.py` - the questions Jev is asked
- `scope_watch/jev_client.py` - live client plus mock mode
- `scope_watch/analyse.py` - thresholds, roll-ups, warnings, evaluation
- `scope_watch/dashboard.py` - the HTML dashboard
- `playground-tests.md` - four cases to try by hand in the TypeSafe Playground

## Hosted demo

The deployable version lives in `public/` and `api/run.js`. It uses the same fictional matter and sends the TypeSafe key only from the server-side Vercel function. Copy `.env.local.example` to `.env.local` for local use, then run `npm install` and `npm run dev`.

## Tuning after the first live run

1. Run `python evaluate.py` and read the mistakes list.
2. If Jev reads a criterion too literally, reword that criterion in `questions.py` (TypeSafe's own advice: put the boundary cases into the criteria text).
3. If too much goes to review, lower `CONFIDENT`; if wrong answers slip through, raise it.
4. Re-run and record the before/after numbers for the demo.
