"""Pure-Python analysis and transparent worklist rules for RideOps.

This is a 30 Sep 2026 snapshot, not a live ticket-system connection.
All durations are wall-clock, IST timestamps as supplied; we do not infer
engineering time or a reopen timestamp from the limited data.
"""
from __future__ import annotations

import csv
import io
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

SNAPSHOT = datetime(2026, 9, 30, 23, 59, 59)
NON_FIX = {
    "Insufficient info - returned to L1", "Config issue - returned to L1",
    "Duplicate of known issue", "Not a bug - how-to", "Not reproducible",
}
RETURNED = {"Insufficient info - returned to L1", "Config issue - returned to L1"}
PRIORITY_POINTS = {"P1": 200, "P2": 130, "P3": 70, "P4": 10}
CHECKS = {
    "Roster / booking not syncing": ["Confirm roster version, shift date/time and booking cutoff", "Compare employee IDs and booking state between roster and dashboard", "Check last sync time; attach anonymised affected-record IDs"],
    "Live tracking / GPS incorrect": ["Capture trip ID, observation time and driver-app GPS status", "Compare client map, driver app and last location timestamp", "Check device/network permissions and whether issue reproduces on another trip"],
    "Report export failing": ["Record report type, filters, date range and export format", "Compare on-screen result count with exported rows", "Check browser/error message; try a small date range"],
    "OTP / boarding issue": ["Capture trip ID, OTP-generation time and boarding state", "Check device clock, network and OTP validity window", "Capture error state without exposing OTP or employee PII"],
    "Billing / invoice discrepancy": ["Record billing period, vendor, rate-card version and invoice ID", "Reconcile affected trip IDs against approved rates", "Check credits, cancelled trips and any manual adjustments"],
    "Login / access issue": ["Confirm account role and desired report access", "Check whether access is enabled for this client and environment", "Capture error message without sharing passwords or tokens"],
    "Cab delay / no-show complaint": ["Confirm trip, schedule, actual pickup/no-show and affected employee count", "Check dispatch timeline and vendor/driver communications", "Record temporary transport/communication mitigation"],
    "Employee address / geocode change": ["Verify requested address and effective date with authorised admin", "Compare saved geocode with route-assigned location", "Check routing cache/sync and impacted trips"],
    "Driver / vehicle compliance docs": ["Verify document type, expiry and verification state", "Check any vehicle or driver assignment restrictions", "Capture document ID/status, not sensitive document contents"],
    "How-to / feature request": ["Confirm existing product capability and relevant permissions", "Share documented steps or workaround with client", "Separate a request for new capability from an actual defect"],
}

def dt(s: str | None) -> datetime | None:
    return datetime.strptime(s, "%Y-%m-%d %H:%M") if s else None


def load_tickets(path: str | Path) -> list[dict[str, Any]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows or len({r["ticket_id"] for r in rows}) != len(rows):
        raise ValueError("Expected nonempty CSV with unique ticket_id values")
    for r in rows:
        r["eng_handoffs"] = int(r["eng_handoffs"] or 0)
        r["reopen_count"] = int(r["reopen_count"] or 0)
        r["csat_score"] = float(r["csat_score"]) if r["csat_score"] else None
    return rows


def hours(start: str | None, end: str | None) -> float | None:
    a,b=dt(start),dt(end)
    return round((b-a).total_seconds()/3600,2) if a and b else None


def ages(t: dict[str, Any]) -> float:
    return max(0, (SNAPSHOT - dt(t["created_at"])).total_seconds() / 86400)


def classify(t: dict[str, Any]) -> tuple[str,str]:
    """Next step, not a claimed root cause or automated disposition."""
    e = t["eng_outcome"]
    owner = t["status"]
    if owner == "Open - with Engineering" and e in RETURNED:
        return ("Confirm ownership", "Engineering's recorded outcome says returned to L1, but the snapshot still assigns engineering. Confirm who has the ball before another handoff.")
    if owner == "Open - with L1" and e == "Insufficient info - returned to L1":
        return ("Rebuild evidence", "Collect reproducible steps and run basic checks before sending this back to engineering.")
    if owner == "Open - with L1" and e == "Config issue - returned to L1":
        return ("Check configuration", "Validate the client's current configuration and apply a supported correction or document why engineering is still needed.")
    if owner == "Open - with L1" and e == "Fixed":
        return ("Verify fix", "Confirm client-visible behaviour before recording resolution in the source ticket system.")
    if owner == "Open - with Engineering":
        return ("Engineering follow-up", "Ask for current investigation owner, next update time and a specific blocker; share complete evidence where missing.")
    if owner == "Open - with L1" and e:
        return ("L1 follow-through", "Check the known issue, workaround or returned verdict with the client and close only after verification.")
    return ("L1 diagnosis", "Run the category checklist and resolve locally if safe; escalate only with a reproducible packet.")


def score_ticket(t: dict[str, Any]) -> int:
    age=ages(t)
    # Severity leads; ageing and churn are tie-breakers, not inferred SLAs.
    return (PRIORITY_POINTS[t["priority"]] + int(min(age, 10)*3)
            + (10 if t["eng_handoffs"]>=2 else 0)
            + (8 if t["eng_outcome"] in RETURNED else 0)
            + (6 if t["reopen_count"]>0 else 0))


def ticket_view(t: dict[str, Any]) -> dict[str, Any]:
    lane,reason=classify(t)
    age=ages(t)
    return {**t, "age_days":round(age,2), "score":score_ticket(t),
            "lane":lane,"recommendation":reason, "checks": CHECKS.get(t["category"],[]),
            "signals": (["P1 critical priority"] if t["priority"]=="P1" else [])
              + (["72h+ in queue"] if age>=3 else [])
              + (["2+ engineering handoffs"] if t["eng_handoffs"]>=2 else [])
              + (["Previously reopened"] if t["reopen_count"]>0 else [])
              + (["Returned for evidence/config"] if t["eng_outcome"] in RETURNED else [])}


def historical_months(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    months = ["2026-07", "2026-08", "2026-09"]
    result=[]
    for m in months:
        end = {"2026-07":"2026-07-31 23:59", "2026-08":"2026-08-31 23:59", "2026-09":"2026-09-30 23:59"}[m]
        e=dt(end)
        created=sum(r["created_at"][:7]==m for r in rows)
        closed=sum(r["final_closed_at"][:7]==m for r in rows)
        # End-of-period balance assumes tickets continuously open until final closure.
        # Reopen timestamps are absent, so historical intermediate backlog is an estimate.
        backlog=sum(dt(r["created_at"])<=e and
                    (not r["final_closed_at"] or dt(r["final_closed_at"])>e) for r in rows)
        result.append({"month":m,"arrivals":created,"final_closures":closed,"estimated_backlog":backlog})
    return result


def weekly_flows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    first=dt("2026-07-02 00:00")
    current=first+timedelta(days=(6-first.weekday())%7)
    out=[]
    while current<=SNAPSHOT+timedelta(days=6):
        low=current-timedelta(days=6)
        upper=min(current.replace(hour=23,minute=59,second=59), SNAPSHOT)
        if low>SNAPSHOT:break
        out.append({"week_end":current.date().isoformat(),"arrivals":sum(low<=dt(r["created_at"])<=upper for r in rows),
           "final_closures":sum(bool(r["final_closed_at"]) and low<=dt(r["final_closed_at"])<=upper for r in rows)})
        current+=timedelta(days=7)
    return out


def summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    opened=[r for r in rows if r["status"]!="Closed"]
    esc=[r for r in rows if r["escalated_to_eng"]=="Yes"]
    closed_e=[hours(r["created_at"],r["final_closed_at"]) for r in esc if r["final_closed_at"]]
    closed_l1=[hours(r["created_at"],r["final_closed_at"]) for r in rows if r["escalated_to_eng"]=="No" and r["final_closed_at"]]
    from statistics import median
    cat=Counter(r["category"] for r in opened)
    return {"total":len(rows), "open":len(opened),
      "open_escalated":sum(r["escalated_to_eng"]=="Yes" for r in opened),
      "open_returned":sum(r["eng_outcome"] in RETURNED for r in opened),
      "open_aged_72h":sum(ages(r)>=3 for r in opened),
      "open_top_two":cat["Roster / booking not syncing"]+cat["Live tracking / GPS incorrect"],
      "escalated_all":len(esc), "non_fix_escalations":sum(r["eng_outcome"] in NON_FIX for r in esc),
      "info_config_returned":sum(r["eng_outcome"] in RETURNED for r in esc),
      "median_closed_escalated_h":round(median(closed_e),1),
      "median_closed_non_escalated_h":round(median(closed_l1),1),
      "categories_open":[{"label":cat_name,"count":count} for cat_name,count in cat.most_common()],
      "monthly":historical_months(rows), "weekly":weekly_flows(rows),
      "snapshot_date":"2026-09-30 23:59 IST"}

REQUIRED_PACKET_FIELDS = ("impact", "steps", "expected", "observed", "checks")
PACKET_FIELDS = REQUIRED_PACKET_FIELDS + ("evidence", "client_update", "engineering_question")

def validate_packet(data: dict[str, Any], valid_ids: set[str]) -> dict[str,str]:
    ticket_id=str(data.get("ticket_id","")).strip()
    if ticket_id not in valid_ids:raise ValueError("Unknown ticket ID")
    values={k:str(data.get(k,"")).strip()[:3000] for k in PACKET_FIELDS}
    missing=[k.replace('_',' ') for k in REQUIRED_PACKET_FIELDS if len(values[k])<5]
    if missing:raise ValueError("Complete required handoff fields: "+", ".join(missing))
    return values


def packet_as_text(t: dict[str, Any], info: dict[str,str])->str:
    lines=[f"RIDEOPS | Engineering handoff for {t['ticket_id']}",
           f"Client: {t['client_name']} ({t['client_tier']}) | {t['priority']} | {t['category']}",
           f"L1 owner: {t['assigned_agent']} | Engineering ticket: {t['eng_ticket_id'] or 'Not linked'}",
           f"Snapshot context: {t['description']}","", "CLIENT IMPACT", info['impact'],
           "", "REPRODUCTION STEPS", info['steps'], "", "EXPECTED", info['expected'],
           "", "OBSERVED", info['observed'], "", "L1 CHECKS COMPLETED", info['checks'],
           "", "EVIDENCE REFERENCES", info['evidence'] or "Not provided",
           "", "LATEST CLIENT UPDATE", info['client_update'] or "Not recorded",
           "", "PRECISE ENGINEERING QUESTION", info['engineering_question'] or "Please investigate the reproduced discrepancy.",
           "", "Prepared by Recovery Desk. Review before sharing; no live CRM/engineering sync."]
    return "\n".join(lines)


def write_csv(records: list[dict[str, Any]], columns: list[str]) -> str:
    output=io.StringIO()
    w=csv.DictWriter(output,fieldnames=columns,extrasaction="ignore")
    w.writeheader();w.writerows(records)
    return output.getvalue()
