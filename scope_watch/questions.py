"""The narrow questions Jev answers. Everything numeric stays in code.

Questions are plain dicts in the TypeSafe API format, which the Python SDK
accepts directly, so the same definitions serve live and mock runs.
"""


def request_questions(eng):
    agreed = [f"{w['name']}: {w['description']}" for w in eng["workstreams"]]
    workstream_criteria = {w["id"]: f"{w['name']}: {w['description']}" for w in eng["workstreams"]}
    workstream_criteria["none"] = "The request does not relate to any of these workstreams."
    return {
        "scope": {
            "type": "choice",
            "instructions": {
                "question": (
                    "The firm acts for the lenders. Does this client request ask for work inside the agreed "
                    "scope in `agreed_scope`, work listed in `exclusions`, or work that cannot be placed clearly?"
                ),
                "agreed_scope": agreed,
                "exclusions": eng["exclusions"],
            },
            "criteria": {
                "in_scope": "The requested work falls squarely within one of the workstreams in `agreed_scope`.",
                "out_of_scope": "The requested work matches an item in `exclusions`.",
                "unclear": (
                    "The request stretches an agreed workstream beyond what `agreed_scope` describes, "
                    "or could reasonably be read as either in or out of scope."
                ),
            },
        },
        "workstream": {
            "type": "choice",
            "instructions": "Which agreed workstream does the requested work relate to most closely?",
            "criteria": workstream_criteria,
        },
    }


def time_entry_questions(eng):
    criteria = {w["id"]: f"{w['name']}: {w['description']}" for w in eng["workstreams"]}
    criteria["out_of_scope"] = "Work on an excluded item: " + "; ".join(eng["exclusions"])
    criteria["unclear"] = (
        "The narrative does not say enough to tell which workstream the work belongs to, "
        "or it mixes tasks from several workstreams."
    )
    return {
        "workstream": {
            "type": "choice",
            "instructions": "Which workstream does the work described in `narrative` belong to?",
            "criteria": criteria,
        },
        "vague": {
            "type": "noul",
            "instructions": "Is `narrative` too vague to tell what specific task was performed?",
            "criteria": {
                "true": "Generic wording such as 'work on file', 'emails', 'review documents' or 'attention to matter', with no document, issue or counterparty named.",
                "false": "Names a specific task, document, issue or counterparty.",
            },
        },
        "block": {
            "type": "noul",
            "instructions": "Does `narrative` combine two or more distinct tasks into a single time entry?",
            "criteria": {
                "true": "Several separate tasks (for example drafting, a call and a checklist update) are recorded together.",
                "false": "One task, or one task with its natural sub-steps.",
            },
        },
    }
