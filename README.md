# RideOps Recovery Desk — FDE case study

A working, local-first support-triage tool for the **Support Lead**. It analyses the exact 1,444-ticket case-study CSV, prioritises the 48 tickets open as of **30 September 2026**, recommends a next action, validates engineering handoff packets, and records actions with a persistent audit trail.

**The important distinction:** this is a working v0 on historical data, **not a live ticketing-system integration**. Its action log never changes a ticket's original status or contacts a client/engineer. The data stays on the machine that runs it.

## Start in under a minute

**Requirements:** Python **3.10+** and a browser. No packages, API keys, internet connection, database setup, or Node installation needed.

```bash
# From this repository folder
python app.py
```

Then open **http://127.0.0.1:8765** in a browser.

On Windows, `py -3 app.py` is an alternative if `python` is not recognised. Stop the server with `Ctrl+C`.

The first run creates `.local/recoverydesk.db`, a SQLite file for locally saved actions and handoff packets. To start an isolated demo without changing previous local activity, pass a different database path:

```bash
python app.py --db .local/demo.db
```

To use a fresh support export with the **same 20-column schema**:

```bash
python app.py --csv /path/to/new_export.csv
```

**Important:** The v0 deliberately uses a fixed **30 September 2026 snapshot reference time** for case-study ageing, cohort and month-end visuals. The `--csv` option lets you inspect another export with the same schema; it is **not** a production live-mode switch. Before real use, update the snapshot/date logic and introduce an integration and permissions model.

## What the tool actually does

1. **Prioritises the backlog.** The main screen shows the 48 open tickets, the 30 Sep scorecard, arrival/closure trends and ticket concentrations. Search by client/ticket/description; filter by priority, L1 owner or next-action lane.
2. **Explains the proposed next action.** Ranking is deterministic: **P1 > P2 > P3 > P4**, with age, 2+ engineering handoffs, returned-info/config verdicts and prior reopens as within-priority signals. No opaque ML scores and no reclassification of the source priority.
3. **Checks before re-escalating.** Each category has tailored L1 checks. A handoff packet cannot be saved unless customer impact, reproduction steps, expected behaviour, observed behaviour, and completed checks are all filled in. Optional fields include evidence reference, last client update and the engineer's exact question.
4. **Persists work instead of simulating it.** Validated packets and recorded actions are saved to SQLite; the queue, action history and packet exports are downloadable as CSV. Nothing is sent externally and “fix verified” is a local log event, **not** a source-system closure.

### Example to show in the demo

Open **SUP-11258**. It is a **P1 GPS issue aged ~9.3 days**. Its ticket status says *Open - with Engineering*, but its recorded engineering outcome says *Config issue - returned to L1*. The lane is **Confirm ownership**, because another blind escalation may make the ticket worse. Open the ticket, review the GPS checks, complete an honest handoff packet, save, copy/export and record an owner-confirmation action. Then export the action log.

The example is taken directly from the provided CSV; no case facts are invented. The demonstration should **not** claim the packet was actually sent or that the ticket was resolved.

## Validate the build

```bash
python -m unittest discover -s tests -v
python analyze.py
```

The **12 automated tests** cover the supplied-data totals and reconstructed monthly flow, high-severity ordering, ownership mismatch, required handoff-field validation, API output, SQLite persistence and CSV export. `analyze.py` prints the key numbers used in the four-page write-up. It requires no third-party packages.

## Files

```text
app.py                         HTTP server + API + SQLite persistence
core.py                        CSV metrics, triage rules and packet validation
analyze.py                     Reproducible numerical audit
web/index.html                 Browser UI
web/styles.css                 Styling
web/app.js                     Client interactions
 data/rideops_support_tickets.csv     Original supplied source data
 data/rideops_data_dictionary.csv    Original supplied schema notes
 tests/test_core.py            Automated regression/API tests
 docs/Case_Study_Writeup.pdf   Main submission (exactly 4 pages)
 docs/WRITEUP_SOURCE.md        Editable reasoning and expanded narrative
 docs/ANALYSIS_AUDIT.txt       Reproduced figures
 docs/DEMO_GUIDE.md            15-minute walkthrough + Q&A prep
```

## Data limitations and guardrails

- **Snapshot, not live:** statuses are as of 30 Sep 2026; no automatic client updates or helpdesk writes.
- **Historical month-end count:** reconstructed from creation and final closure. Because actual reopen timestamps are unavailable, July's 30 and August's 23 are upper bounds, not exact historical snapshots (lower bounds 26 and 20 respectively). September's **48** is directly observed.
- **End-to-end time ≠ engineering turnaround:** the file lacks handoff entry, return and acceptance timestamps. The 86.8-hour escalated median includes all stages.
- **Non-Fixed ≠ avoidable:** a non-Fixed engineering outcome may still reflect legitimate investigation. We target the narrower 173 cases with info/config return verdicts.
- **CSAT selection:** 648 of 1,444 tickets have scores; do not claim those observations represent all clients.
- **Privacy and safety:** do not paste actual OTPs, access tokens, personal details or unredacted logs into packet fields. For a real pilot, implement RBAC, secure storage/retention and an approved CRM integration.

## Deliberate non-goals

No hiring assumptions, no AI chatbot, no auto-closing, no guessed SLA, no background monitoring, and no live client/engineering notifications. The goal is to prove whether a better support-to-engineering handoff loop can reduce ageing and rework before investing in automation.

## Deliverable fit

The case brief permits a **repo with a short README on how to run it** instead of a hosted link. This folder is that runnable repository; pair it with `docs/Case_Study_Writeup.pdf`. For submission, upload the folder to a private repository and share reader access, or attach a ZIP if the recruiter accepts attachments. Do not claim a hosted URL unless you actually deploy it.
