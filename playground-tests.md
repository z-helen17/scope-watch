# Playground tests (paste into console.typesafe.ai/playground)

Try these by hand before running the code. Paste the state into the state box and the questions JSON into the questions box, then compare the answers with the expected ones.

## 1. A client request that should come back out of scope

State:
```json
{
  "subject": "Hedge documents",
  "message": "The hedge provider has sent over their draft ISDA schedule and a confirmation. Could you take a look and let us know if anything stands out?"
}
```

Questions:
```json
{
  "scope": {
    "type": "choice",
    "instructions": {
      "question": "The firm acts for the lenders. Does this client request ask for work inside the agreed scope in `agreed_scope`, work listed in `exclusions`, or work that cannot be placed clearly?",
      "agreed_scope": [
        "Legal due diligence: Legal due diligence on the project for the lenders: the borrower's organisational documents, real estate for the project site as defined in the term sheet (wind leases, easements, title commitments and ALTA surveys), existing federal, state and county permits, the ERCOT interconnection agreement, and the material project contracts (turbine supply, balance-of-plant, O&M, PPA). Includes the written due diligence memo and calls with Texas local counsel.",
        "Credit agreement: Drafting and negotiating the New York-law credit agreement for the lenders: financial covenants, distribution conditions, ESG and reporting covenants, events of default, and negotiation calls with borrower's counsel.",
        "Collateral package: Drafting, negotiating and perfecting the lenders' collateral: pledge of the borrower's membership interests, deed of trust over the leases and easements, security agreement, account control agreements, consents to collateral assignment from project counterparties, and UCC and county recording filings to perfect them.",
        "Conditions precedent and first funding: Preparing and running the closing checklist, reviewing deliverables from the borrower, the lenders' enforceability opinion, and the first funding."
      ],
      "exclusions": [
        "Hedging documentation (ISDA master agreement, schedules, confirmations) or advice on hedging",
        "Tax advice, tax equity financing or tax credit transfer arrangements",
        "Intercreditor, subordination or other arrangements with any mezzanine, tax equity or sponsor lender",
        "Advice to the borrower or sponsor, or preparing documents on their side of the deal",
        "Disputes, claims, litigation or arbitration",
        "Applications for new permits, interconnection requests or other regulatory filings (reviewing existing permits is included)",
        "Refinancing, or amendments and waivers after first funding"
      ]
    },
    "criteria": {
      "in_scope": "The requested work falls squarely within one of the workstreams in `agreed_scope`.",
      "out_of_scope": "The requested work matches an item in `exclusions`.",
      "unclear": "The request stretches an agreed workstream beyond what `agreed_scope` describes, or could reasonably be read as either in or out of scope."
    }
  },
  "workstream": {
    "type": "choice",
    "instructions": "Which agreed workstream does the requested work relate to most closely?",
    "criteria": {
      "dd": "Legal due diligence: Legal due diligence on the project for the lenders: the borrower's organisational documents, real estate for the project site as defined in the term sheet (wind leases, easements, title commitments and ALTA surveys), existing federal, state and county permits, the ERCOT interconnection agreement, and the material project contracts (turbine supply, balance-of-plant, O&M, PPA). Includes the written due diligence memo and calls with Texas local counsel.",
      "facility": "Credit agreement: Drafting and negotiating the New York-law credit agreement for the lenders: financial covenants, distribution conditions, ESG and reporting covenants, events of default, and negotiation calls with borrower's counsel.",
      "security": "Collateral package: Drafting, negotiating and perfecting the lenders' collateral: pledge of the borrower's membership interests, deed of trust over the leases and easements, security agreement, account control agreements, consents to collateral assignment from project counterparties, and UCC and county recording filings to perfect them.",
      "cps": "Conditions precedent and first funding: Preparing and running the closing checklist, reviewing deliverables from the borrower, the lenders' enforceability opinion, and the first funding.",
      "none": "The request does not relate to any of these workstreams."
    }
  }
}
```
Expected: scope = out_of_scope with high confidence.

## 2. A request that should come back unclear or low-confidence

State:
```json
{
  "subject": "Substation parcels",
  "message": "The sponsor has added two parcels for the substation that weren't in the original site plan. Can you extend the due diligence to cover them?"
}
```
Use the same questions. Expected: unclear, or a split between in_scope and unclear (low confidence).

## 3. A time entry that should be flagged as block billing

State:
```json
{
  "narrative": "Revise pledge agreement, deed of trust and account control agreements following borrower comments; call with title company on recording; update closing checklist",
  "timekeeper_role": "Senior Associate"
}
```

Questions:
```json
{
  "workstream": {
    "type": "choice",
    "instructions": "Which workstream does the work described in `narrative` belong to?",
    "criteria": {
      "dd": "Legal due diligence: Legal due diligence on the project for the lenders: the borrower's organisational documents, real estate for the project site as defined in the term sheet (wind leases, easements, title commitments and ALTA surveys), existing federal, state and county permits, the ERCOT interconnection agreement, and the material project contracts (turbine supply, balance-of-plant, O&M, PPA). Includes the written due diligence memo and calls with Texas local counsel.",
      "facility": "Credit agreement: Drafting and negotiating the New York-law credit agreement for the lenders: financial covenants, distribution conditions, ESG and reporting covenants, events of default, and negotiation calls with borrower's counsel.",
      "security": "Collateral package: Drafting, negotiating and perfecting the lenders' collateral: pledge of the borrower's membership interests, deed of trust over the leases and easements, security agreement, account control agreements, consents to collateral assignment from project counterparties, and UCC and county recording filings to perfect them.",
      "cps": "Conditions precedent and first funding: Preparing and running the closing checklist, reviewing deliverables from the borrower, the lenders' enforceability opinion, and the first funding.",
      "out_of_scope": "Work on an excluded item: Hedging documentation (ISDA master agreement, schedules, confirmations) or advice on hedging; Tax advice, tax equity financing or tax credit transfer arrangements; Intercreditor, subordination or other arrangements with any mezzanine, tax equity or sponsor lender; Advice to the borrower or sponsor, or preparing documents on their side of the deal; Disputes, claims, litigation or arbitration; Applications for new permits, interconnection requests or other regulatory filings (reviewing existing permits is included); Refinancing, or amendments and waivers after first funding",
      "unclear": "The narrative does not say enough to tell which workstream the work belongs to, or it mixes tasks from several workstreams."
    }
  },
  "vague": {
    "type": "noul",
    "instructions": "Is `narrative` too vague to tell what specific task was performed?",
    "criteria": {
      "true": "Generic wording such as 'work on file', 'emails', 'review documents' or 'attention to matter', with no document, issue or counterparty named.",
      "false": "Names a specific task, document, issue or counterparty."
    }
  },
  "block": {
    "type": "noul",
    "instructions": "Does `narrative` combine two or more distinct tasks into a single time entry?",
    "criteria": {
      "true": "Several separate tasks (for example drafting, a call and a checklist update) are recorded together.",
      "false": "One task, or one task with its natural sub-steps."
    }
  }
}
```
Expected: block close to 1, workstream unclear or low confidence.

## 4. A vague entry

State:
```json
{
  "narrative": "Work on file",
  "timekeeper_role": "Paralegal"
}
```
Use the time-entry questions. Expected: vague close to 1, workstream unclear.
