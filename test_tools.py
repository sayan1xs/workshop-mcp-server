"""Tests for the workshop tools.

These call the tool functions directly rather than going through the MCP
protocol - the protocol layer is the SDK's job to get right, the queries are
mine. Run with:

    python seed_data.py && python test_tools.py
"""

import sqlite3

from server import (
    add_job_note,
    jobs_blocked_on_parts,
    parts_availability,
    search_jobs,
    technician_schedule,
    vehicle_history,
)

passed = 0


def check(label: str, condition: bool) -> None:
    global passed
    if not condition:
        raise AssertionError(f"FAILED: {label}")
    passed += 1
    print(f"  ok  {label}")


print("search_jobs")
all_open = search_jobs(status="open", limit=50)
check("returns the open jobs", all_open["count"] == 12)
check("every result really is open",
      all(j["status"] in ("booked", "in_progress", "waiting_parts")
          for j in all_open["jobs"]))
check("filters by status", search_jobs(status="waiting_parts")["count"] == 3)
check("finds a plate written without a space",
      search_jobs(reg="mt66zxb")["count"] > 0)
check("finds a plate from a partial match",
      search_jobs(reg="MT66")["count"] > 0)
check("filters by technician",
      all(j["technician"] == "Derek Lowrie"
          for j in search_jobs(technician="Derek")["jobs"]))
check("respects the limit", len(search_jobs(limit=3)["jobs"]) == 3)
no_match = search_jobs(reg="ZZ99 ZZZ")
check("reports an empty result instead of returning nothing",
      no_match["count"] == 0 and "message" in no_match)

print("\nvehicle_history")
hist = vehicle_history("MT66 ZXB")
check("finds the vehicle", hist["found"] is True)
check("returns the whole history", hist["visits"] == 3)
check("newest visit first",
      hist["history"][0]["opened_date"] >= hist["history"][-1]["opened_date"])
check("surfaces the repeat starting fault",
      sum("starting fault" in v["description"] for v in hist["history"]) == 2)
check("includes technician notes", len(hist["notes"]) >= 1)
missing = vehicle_history("AA00 AAA")
check("handles an unknown plate", missing["found"] is False)

print("\nparts_availability")
low = parts_availability(only_low_stock=True)
check("finds the parts at or below reorder level", low["count"] == 6)
check("flags them", all(p["needs_reorder"] for p in low["parts"]))
check("searches by name", parts_availability(query="clutch")["count"] == 1)
check("searches by SKU", parts_availability(query="brk-")["count"] == 2)
check("handles no match",
      parts_availability(query="flux capacitor")["count"] == 0)

print("\njobs_blocked_on_parts")
blocked = jobs_blocked_on_parts()
check("finds the blocked jobs", blocked["count"] == 3)
check("every one is genuinely short",
      all(b["in_stock"] < b["qty_needed"] for b in blocked["blocked"]))
check("computes the shortfall",
      all(b["shortfall"] == b["qty_needed"] - b["in_stock"]
          for b in blocked["blocked"]))
check("computes days open",
      all(b["days_open"] >= 0 for b in blocked["blocked"]))
check("catches the job needing 2 of a part with 1 in stock",
      any(b["job_card"] == 1015 and b["shortfall"] == 1
          for b in blocked["blocked"]))

print("\ntechnician_schedule")
today = technician_schedule()
check("defaults to today", today["count"] == 4)
check("totals the booked hours", today["booked_hours"] > 0)
check("computes each booking's length",
      all(b["hours"] > 0 for b in today["bookings"]))
check("accepts 'tomorrow'", technician_schedule(day="tomorrow")["count"] == 3)
check("filters by technician",
      all(b["technician"] == "Ciara Bannon"
          for b in technician_schedule(technician="Ciara")["bookings"]))
check("rejects an unreadable date",
      "error" in technician_schedule(day="next Tuesday-ish"))
check("handles a day with nothing booked",
      technician_schedule(day="1999-01-01")["count"] == 0)

print("\nadd_job_note")
before = len(vehicle_history("MT66 ZXB")["notes"])
written = add_job_note(1013, "Chased supplier, cat converter due Thursday.",
                       author="Nick")
check("reports success", written["written"] is True)
check("returns the job it attached to", written["job_card"] == 1013)
check("echoes the vehicle back", written["vehicle"] == "MT66 ZXB")
check("actually persisted",
      len(vehicle_history("MT66 ZXB")["notes"]) == before + 1)
check("rejects an unknown job card",
      add_job_note(9999, "test")["written"] is False)
check("rejects an empty note",
      add_job_note(1013, "   ")["written"] is False)

print("\nread tools cannot write")
try:
    from server import _connect
    _connect().execute("DELETE FROM job_cards")
    raise AssertionError("FAILED: read connection allowed a write")
except sqlite3.OperationalError:
    passed += 1
    print("  ok  read-only connection refuses a DELETE")

print(f"\n{passed} checks passed.")
