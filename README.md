# RideOps Recovery Desk

**FDE Case Study — Support Operations**

RideOps Recovery Desk is a local support-triage tool built around the 1,444-ticket case-study dataset.

The goal is to help a Support Lead review the open backlog, identify tickets that need attention, and improve the quality of engineering escalations. The tool focuses on the 48 tickets that were open as of 30 September 2026.

It includes a prioritised queue, ticket-level next-action recommendations, engineering handoff validation, and a local action history.

This is a working prototype using the supplied historical data. It does not connect to a live ticketing system, update source ticket statuses, or send messages to customers or engineers. All saved activity stays on the machine running the application.

## Running the application

### Requirements

- Python 3.10 or later
- A web browser

No third-party Python packages, API keys, Node.js installation, or external database are required.

From the project directory, run:

```bash
python app.py
```

Then open:

```text
http://127.0.0.1:8765
```

On Windows, you can also use:

```powershell
py -3 app.py
```

Press `Ctrl+C` in the terminal to stop the server.

### Local storage

On the first run, the application creates:

```text
.local/recoverydesk.db
```

This SQLite database stores locally recorded actions and validated handoff packets.

To run a separate demo without using the existing activity history:

```bash
python app.py --db .local/demo.db
```

### Using another CSV export

The application can also load another export that follows the same 20-column schema:

```bash
python app.py --csv /path/to/new_export.csv
```

The case-study version uses 30 September 2026 as its fixed reference date for ticket ageing and historical reporting. Loading another CSV does not make the application live. The reference-date logic and source-system integration would need to be addressed before operational use.

## What the application covers

### 1. Backlog review

The main screen brings together the open tickets, the September snapshot, arrival and closure trends, and ticket concentrations.

Tickets can be searched using client, ticket ID, or description. The queue can also be filtered by priority, L1 owner, and next-action lane.

### 2. Ticket prioritisation

The ranking logic is deterministic and keeps the original ticket priority unchanged.

Priority order is:

**P1 → P2 → P3 → P4**

Within each priority, the logic considers ticket age, repeated engineering handoffs, returned-for-information or configuration outcomes, and previous reopens.

The purpose is to make the ordering understandable to the person working the queue, rather than relying on an unexplained score.

### 3. Engineering handoff checks

Each ticket category has its own set of L1 checks.

Before a handoff packet can be saved, the following fields must be completed:

- Customer impact
- Reproduction steps
- Expected behaviour
- Observed behaviour
- Checks already completed by L1

There are also optional fields for evidence references, the last customer update, and the specific question for engineering.

This is intended to reduce incomplete escalations and make the information being passed to engineering more useful.

### 4. Action history and exports

Validated packets and recorded actions are stored in the local SQLite database.

The application also supports CSV exports of the queue, action history, and handoff packets.

Recording an action does not change the original ticket status. For example, a local "fix verified" entry is an audit-log event, not confirmation that the source ticketing system has been closed.

## Example ticket for the demo

A useful example is **SUP-11258**.

It is a P1 GPS issue, aged approximately 9.3 days in the case-study snapshot. Its ticket status is recorded as *Open - with Engineering*, while its engineering outcome is *Config issue - returned to L1*.

The application places it in the **Confirm ownership** lane.

This is worth reviewing before another escalation is made. The demo can be used to inspect the GPS checks, complete a handoff packet, save it locally, record an owner-confirmation action, and export the action history.

The example comes from the supplied CSV. The demonstration does not imply that the packet was sent or that the ticket was resolved.

## Running the checks

Run the automated tests with:

```bash
python -m unittest discover -s tests -v
```

To reproduce the numerical analysis used in the case-study write-up:

```bash
python analyze.py
```

The test suite contains 12 tests covering supplied-data totals, reconstructed monthly flow, priority ordering, ownership mismatch, handoff-field validation, API output, SQLite persistence, and CSV export.

Both commands use the Python standard library.

## Project structure

```text
app.py
    HTTP server, API endpoints, and SQLite persistence

core.py
    CSV processing, metrics, triage rules, and packet validation

analyze.py
    Reproducible numerical analysis

web/
    index.html
    styles.css
    app.js

data/
    rideops_support_tickets.csv
    rideops_data_dictionary.csv

tests/
    test_core.py

docs/
    Case_Study_Writeup.pdf
    
```

## Data notes and limitations

A few limitations matter when interpreting the results.

- **Historical snapshot:** The application uses ticket data as of 30 September 2026. It is not connected to a live support queue.
- **Month-end backlog reconstruction:** July's estimated month-end count is an upper bound of 30, with a possible range of 26–30. August's upper bound is 23, with a possible range of 20–23. Reopen timestamps are not available to reconstruct exact historical snapshots. September's count of 48 is directly observed.
- **Closure time:** The median of 86.8 hours for escalated tickets is end-to-end closure time, not engineering turnaround time. The dataset does not contain the timestamps needed to isolate engineering handling time.
- **Engineering outcomes:** A non-Fixed outcome does not automatically mean an escalation was avoidable. The analysis focuses on the narrower group of 173 cases returned for information or configuration.
- **CSAT coverage:** Only 648 of the 1,444 tickets have CSAT scores. Those responses should not be treated as representative of every customer.
- **Privacy:** Do not enter real OTPs, access tokens, personal details, or unredacted logs into handoff fields.

A real operational pilot would also need role-based access, appropriate data retention and secure storage, and an approved integration with the ticketing system.

## Possible next steps

The prototype could be extended with a live ticketing-system integration, role-based permissions, updated ageing logic, and a controlled workflow for sending and tracking engineering handoffs. Those capabilities are outside the scope of this case-study version.