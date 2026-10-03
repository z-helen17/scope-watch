"""Thin wrapper around TypeSafe's Jev, with a mock mode for building without an API key.

Live mode needs TYPESAFE_API_KEY in the environment (a local .env file is fine).
Mock mode invents plausible answers from the test labels so the pipeline and the
dashboard can be built and demoed offline. Mock output is always marked as such.
"""
import hashlib
import os
import random


def _rng(key):
    seed = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:12], 16)
    return random.Random(seed)


def _choice_confidence(probs):
    n = len(probs)
    peak = max(probs.values())
    return max(0.0, min(1.0, (n * peak - 1) / (n - 1))) if n > 1 else 1.0


class JevClient:
    def __init__(self, mock=False, model="jev-latest"):
        self.mock = mock
        self.model = model
        self.model_used = "mock" if mock else None
        self.input_tokens = 0
        self.calls = 0
        self._client = None
        if not mock:
            try:
                from typesafe_sdk import TypeSafeClient
            except ImportError as exc:
                raise SystemExit("typesafe-sdk is not installed. Run: pip install -r requirements.txt") from exc
            if not os.environ.get("TYPESAFE_API_KEY"):
                raise SystemExit("TYPESAFE_API_KEY is not set. Add it to a .env file or run with --mock.")
            self._client = TypeSafeClient()

    def ask(self, item_id, state, questions, hints=None):
        """Return {question_id: answer_dict}. `hints` (test labels) are only used in mock mode."""
        self.calls += 1
        if self.mock:
            return self._mock(item_id, questions, hints or {})
        resp = self._client.system_one(state=state, questions=questions, model=self.model)
        self.model_used = resp.model
        if resp.usage and resp.usage.input_tokens:
            self.input_tokens += resp.usage.input_tokens
        out = {}
        for qid, ans in resp.answers.items():
            d = ans.model_dump() if hasattr(ans, "model_dump") else dict(ans)
            out[qid] = d
        return out

    def close(self):
        if self._client is not None and hasattr(self._client, "close"):
            self._client.close()

    # ---------- mock ----------
    def _mock(self, item_id, questions, hints):
        out = {}
        for qid, q in questions.items():
            r = _rng(f"{item_id}:{qid}")
            if q["type"] == "choice":
                options = list(q["criteria"].keys())
                target = hints.get(qid)
                hard = hints.get(f"{qid}_hard", False)
                if target not in options:
                    target = r.choice(options)
                if hard:
                    # Spread the probability so confidence comes out low, as Jev should on genuinely ambiguous items.
                    alt = r.choice([o for o in options if o != target])
                    p_t = r.uniform(0.38, 0.5)
                    p_a = r.uniform(0.25, 0.35)
                    rest = (1 - p_t - p_a) / max(1, len(options) - 2)
                    probs = {o: rest for o in options}
                    probs[target], probs[alt] = p_t, p_a
                else:
                    p_t = r.uniform(0.78, 0.97)
                    rest = (1 - p_t) / (len(options) - 1)
                    probs = {o: rest for o in options}
                    probs[target] = p_t
                choice = max(probs, key=probs.get)
                out[qid] = {
                    "type": "choice",
                    "choice": choice,
                    "confidence": round(_choice_confidence(probs), 3),
                    "probabilities": {k: round(v, 3) for k, v in probs.items()},
                }
            elif q["type"] == "noul":
                truth = hints.get(qid)
                val = r.uniform(0.82, 0.97) if truth else r.uniform(0.02, 0.15)
                out[qid] = {"type": "noul", "noul": round(val, 3)}
        return out
