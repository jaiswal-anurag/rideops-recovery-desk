# 15-minute live demo + 10-minute questions

The demo should feel like a support-lead working session, not a slide narration. Keep the app open and the original CSV on hand.

| Time | Show | Suggested words |
|---|---|---|
| 0:00–1:30 | One-page thesis | “We have a flow problem. Arrivals grew 52%, and repeated handoff loops appear in the same two categories that dominate the open queue.” |
| 1:30–4:00 | Monthly chart and current counts | “July's 30 is an approximate upper bound due to missing reopen timestamps; September's 48 is the snapshot truth. 34 open tickets were escalated.” |
| 4:00–6:00 | Sort/filter the queue | “I chose support lead as my first user. Severity always comes first; everything after that is transparent tie-breaking.” |
| 6:00–9:00 | SUP-11258 | “This P1 GPS ticket is 9.3 days old; it says with Engineering but its outcome says returned to L1. Before sending it anywhere, someone should confirm ownership.” |
| 9:00–12:00 | Handoff packet | “Here is the category checklist. Empty or vague five-field packets are rejected. I can copy/export a complete human-reviewed packet.” |
| 12:00–13:30 | Log an action + CSV export | “Action is saved to SQLite, and I can hand off an audit export. It doesn't falsely mark a production ticket closed.” |
| 13:30–15:00 | Pilot measures + roadmap | “In four weeks I'd test whether 72h+ and returned-info/config work goes down without worse reopens, then earn the right to integrate.” |

## Suggested safe demonstration packet (clearly label it as illustrative)

Select SUP-11258, but **do not present the following invented reproduction details as actual case data**. Use them only to show how a form could be filled after a real agent collects evidence:

- Client impact: `Illustrative: transport admin reports unreliable driver positions for affected rides; impact count needs confirmation.`
- Reproduction: `Illustrative: open trip tracking view, watch driver marker update for 5 minutes, record trip ID and timestamps.`
- Expected: `Location marker follows the driver's latest reported coordinates.`
- Observed: `Ticket says driver-app GPS jumps between locations; exact timestamps and logs not supplied.`
- Checks: `Illustrative demo checklist only; actual L1 checks not yet verified. Do not send as completed.`

**Better live-demo choice:** use an action log with a note such as `Demo only: owner confirmation needed; no client contact or engineering update made.` That proves persistence without fabricating a production intervention.

## Questions to prepare for

**Q. Why not hire more agents?** No hiring budget was given, and 173/486 engineering outcomes returned as insufficient-info/config. Fixing workflow quality is a faster, measurable first bet. Hiring can be reconsidered with capacity evidence.

**Q. Are 56.6% of escalations unnecessary?** No. That's the share whose engineering outcome was not “Fixed.” Some needed real investigation. The narrower 35.6% returned for missing information or configuration is a better rework opportunity; even those are not automatically avoidable.

**Q. How did you measure engineering slowness?** I didn't; that would be unsupported. We only know full ticket creation-to-final-closure time. For a live pilot, add handoff start, owner acceptance, return, next response and resolution timestamps.

**Q. Why is July backlog 30 if all July cases are closed in September?** The balance from creation to final closure gives an upper bound; four July cases had been closed once by July end and could have been reopened later. Without reopen timestamps, July true month-end open lies between 26 and 30. The 30 Sep total of 48 comes from the actual status field.

**Q. Why start with a support lead, not every support agent?** One support lead can triage across the queue, identify contradictory ownership states and audit handoff quality, while a two-agent pilot tests whether the new workflow is tolerable before rollout.

**Q. Why a rule-based score?** The source already gives severity, status, age, handoffs and reopen flags. There are only 48 open cases; using an ML model would create unverified confidence and more explanation work. Priorities are not overridden.

**Q. Could a mandatory checklist delay P1 incidents?** Yes. Do not block urgent escalation. Treat this as a human-reviewed support aid; allow emergency P1 routing and require evidence after the initial safety response.

**Q. Does a local “verified resolved” action reduce the displayed 48?** No. The app logs that someone verified a client-visible fix; production status must still be updated in the ticket system. A local UI must not fabricate operational improvement.

**Q. What if the backlog keeps increasing while returned escalations fall?** Then inflow or other bottlenecks dominate; we should show arrivals/closures weekly, review team capacity and prevent false celebration of a single quality metric.

**Q. What did you deliberately skip?** Live integration, RBAC and security hardening for actual corporate use, automatic client messaging, AI diagnosis and a new ticketing platform. We should only build those after proving the narrow handoff intervention reduces repeat loops.
