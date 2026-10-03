const fs = require('node:fs');
const path = require('node:path');

const ROOT = process.cwd();
const CONFIDENT = 0.55;
const FLAG_YES = 0.70;
const AMBER_GAP = 10;
const RED_GAP = 25;

function csvRows(text) {
  const lines = text.trim().split(/\r?\n/);
  const headers = lines.shift().split(',');
  return lines.map((line) => {
    const values = [];
    let value = '', quoted = false;
    for (let i = 0; i < line.length; i += 1) {
      const ch = line[i];
      if (ch === '"' && line[i + 1] === '"') { value += '"'; i += 1; }
      else if (ch === '"') quoted = !quoted;
      else if (ch === ',' && !quoted) { values.push(value); value = ''; }
      else value += ch;
    }
    values.push(value);
    return Object.fromEntries(headers.map((h, i) => [h, values[i] || '']));
  });
}

function loadMatter() {
  const data = path.join(ROOT, 'data');
  const engagement = JSON.parse(fs.readFileSync(path.join(data, 'engagement.json'), 'utf8'));
  const requests = JSON.parse(fs.readFileSync(path.join(data, 'requests.json'), 'utf8'));
  const entries = csvRows(fs.readFileSync(path.join(data, 'timesheets.csv'), 'utf8')).map((row) => ({ ...row, hours: Number(row.hours) }));
  return { engagement, requests, entries };
}

function requestQuestions(engagement) {
  const workstreams = Object.fromEntries(engagement.workstreams.map((w) => [w.id, `${w.name}: ${w.description}`]));
  workstreams.none = 'The request does not relate to any agreed workstream.';
  return {
    scope: {
      type: 'choice',
      instructions: { question: 'The firm acts for the lenders. Does this request ask for work inside agreed_scope, work listed in exclusions, or work that cannot be placed clearly?', agreed_scope: engagement.workstreams.map((w) => `${w.name}: ${w.description}`), exclusions: engagement.exclusions },
      criteria: { in_scope: 'The requested work falls squarely within an agreed workstream.', out_of_scope: 'The requested work matches an item in exclusions.', unclear: 'The request stretches an agreed workstream beyond what it describes, or could reasonably be read as either in or out of scope.' }
    },
    workstream: { type: 'choice', instructions: 'Which agreed workstream does the request relate to most closely?', criteria: workstreams }
  };
}

function timeQuestions(engagement) {
  const workstreams = Object.fromEntries(engagement.workstreams.map((w) => [w.id, `${w.name}: ${w.description}`]));
  workstreams.out_of_scope = `Work on an excluded item: ${engagement.exclusions.join('; ')}`;
  workstreams.unclear = 'The narrative does not say enough to tell which workstream it belongs to, or it mixes tasks from several workstreams.';
  return {
    workstream: { type: 'choice', instructions: 'Which workstream does the work described in narrative belong to?', criteria: workstreams },
    vague: { type: 'noul', instructions: 'Is narrative too vague to tell what specific task was performed?', criteria: { true: "Generic wording such as 'work on file', 'emails', 'review documents' or 'attention to matter', with no document, issue or counterparty named.", false: 'Names a specific task, document, issue or counterparty.' } },
    block: { type: 'noul', instructions: 'Does narrative combine two or more distinct tasks into one time entry?', criteria: { true: 'Separate pieces of work that could be billed independently are combined, for example drafting several different documents plus a call and a checklist update, or an unrelated call bundled with document work.', false: 'One coherent task with its natural sub-steps. Reviewing a document or a related document set and recording findings, comments, issues or a summary is one task; negotiating one document and updating it for comments is one task.' } }
  };
}

async function ask(state, questions) {
  const response = await fetch('https://api.typesafe.ai/v1/systemone', {
    method: 'POST',
    headers: { Authorization: `Bearer ${process.env.TYPESAFE_API_KEY}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: 'jev-latest', state, questions })
  });
  if (!response.ok) throw new Error(`TypeSafe returned ${response.status}: ${await response.text()}`);
  return response.json();
}

function requestResult(request, answers, names) {
  const scope = answers.scope;
  const workstream = answers.workstream;
  const review = scope.confidence < CONFIDENT || scope.choice === 'unclear';
  const outside = scope.choice === 'out_of_scope' && !review;
  return {
    ...request, scope: scope.choice, confidence: scope.confidence, probabilities: scope.probabilities,
    workstream: workstream.choice, severity: review ? 'review' : outside ? 'high' : 'ok',
    action: review ? 'Partner to decide before any work starts' : outside ? 'Outside agreed scope: agree a fee before starting' : `Proceed under ${names[workstream.choice] || 'the agreed scope'}`
  };
}

function entryResult(entry, answers, rates) {
  const workstream = answers.workstream;
  const vague = answers.vague.noul;
  const block = answers.block.noul;
  const review = workstream.confidence < CONFIDENT || workstream.choice === 'unclear';
  const issues = [];
  if (workstream.choice === 'out_of_scope' && !review) issues.push('Time on excluded work: agree a fee or write it off');
  if (vague > FLAG_YES) issues.push('Narrative too vague to bill: rewrite before invoicing');
  if (block > FLAG_YES) issues.push('Several tasks in one entry: split before billing');
  if (review) issues.push('Workstream unclear: matter manager to confirm');
  return { ...entry, fees: Number((entry.hours * rates[entry.role]).toFixed(2)), workstream: workstream.choice, confidence: workstream.confidence, vague, block, review, issues };
}

function rollup(engagement, entries) {
  return engagement.workstreams.map((workstream) => {
    const mine = entries.filter((entry) => entry.workstream === workstream.id);
    const periodFees = mine.reduce((sum, entry) => sum + entry.fees, 0);
    const spent = workstream.billed_before_period + periodFees;
    const burn = spent / workstream.budget_fees * 100;
    const projected = workstream.pct_complete ? spent / (workstream.pct_complete / 100) : null;
    const gap = burn - workstream.pct_complete;
    const rag = gap > RED_GAP || (burn >= 90 && workstream.pct_complete < 90) ? 'red' : gap > AMBER_GAP || (projected && projected > workstream.budget_fees * 1.1) ? 'amber' : 'green';
    return { id: workstream.id, name: workstream.name, budget: workstream.budget_fees, spent, burn, complete: workstream.pct_complete, projected, rag };
  });
}

async function analyse() {
  const { engagement, requests, entries } = loadMatter();
  const requestQs = requestQuestions(engagement);
  const timeQs = timeQuestions(engagement);
  const names = Object.fromEntries(engagement.workstreams.map((w) => [w.id, w.name]));
  const requestResponses = await Promise.all(requests.map(async (request) => ({ request, response: await ask({ subject: request.subject, message: request.body }, requestQs) })));
  const entryResponses = await Promise.all(entries.map(async (entry) => ({ entry, response: await ask({ narrative: entry.narrative, timekeeper_role: entry.role }, timeQs) })));
  const requestResults = requestResponses.map(({ request, response }) => requestResult(request, response.answers, names));
  const entryResults = entryResponses.map(({ entry, response }) => entryResult(entry, response.answers, engagement.rates));
  const workstreams = rollup(engagement, entryResults);
  const flags = [
    ...workstreams.filter((w) => w.rag !== 'green').map((w) => ({ severity: w.rag, title: `${w.name}: ${w.burn.toFixed(0)}% of budget spent, ${w.complete}% of work complete` })),
    ...requestResults.filter((r) => r.severity === 'high').map((r) => ({ severity: 'red', title: `Out-of-scope request: ${r.subject}` })),
    ...entryResults.filter((e) => e.issues.length).map((e) => ({ severity: 'amber', title: `Time entry needs attention: ${e.id}` }))
  ];
  return { matter: engagement.matter, workstreams, requests: requestResults, entries: entryResults, flags, calls: requests.length + entries.length };
}

// The demo matter never changes, so one live Jev run is reused instead of
// spending the API key on every click: the function keeps the result in memory
// (concurrent requests share one in-flight run) and the CDN caches it for a day.
let cached = null;

module.exports = async (req, res) => {
  if (req.method !== 'GET') return res.status(405).json({ error: 'Use GET.' });
  if (req.url.includes('?')) return res.status(400).json({ error: 'No parameters accepted.' });
  if (!process.env.TYPESAFE_API_KEY) return res.status(500).json({ error: 'TYPESAFE_API_KEY is not configured on this deployment.' });
  try {
    if (!cached) cached = analyse().catch((error) => { cached = null; throw error; });
    const result = await cached;
    res.setHeader('Cache-Control', 'public, max-age=0, s-maxage=86400, stale-while-revalidate=86400');
    return res.status(200).json(result);
  } catch (error) {
    res.setHeader('Cache-Control', 'no-store');
    return res.status(500).json({ error: error.message });
  }
};
