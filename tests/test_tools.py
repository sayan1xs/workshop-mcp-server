"""Tests for the workshop tools.

These call the tool functions directly rather than going through the MCP
protocol. The protocol layer is the SDK's job to get right; the queries are
mine, and the queries are what can quietly be wrong.

    uv run pytest
"""

from __future__ import annotations

import sqlite3

import pytest

from workshop.db import connect
from workshop.server import (
    add_job_note,
    jobs_blocked_on_parts,
    parts_availability,
    search_jobs,
    technician_schedule,
    vehicle_history,
)

# --------------------------------------------------------------------------
# search_jobs
# --------------------------------------------------------------------------


def test_returns_the_open_jobs() -> None:
    assert search_jobs(status="open", limit=50)["count"] == 12


def test_every_open_result_really_is_open() -> None:
    jobs = search_jobs(status="open", limit=50)["jobs"]
    assert all(j["status"] in ("booked", "in_progress", "waiting_parts") for j in jobs)


def test_filters_by_status() -> None:
    assert search_jobs(status="waiting_parts")["count"] == 3


def test_finds_a_plate_written_without_a_space() -> None:
    assert search_jobs(reg="mt66zxb")["count"] > 0


def test_finds_a_plate_from_a_partial_match() -> None:
    assert search_jobs(reg="MT66")["count"] > 0


def test_filters_by_technician() -> None:
    jobs = search_jobs(technician="Derek")["jobs"]
    assert jobs and all(j["technician"] == "Derek Lowrie" for j in jobs)


def test_respects_the_limit() -> None:
    assert len(search_jobs(limit=3)["jobs"]) == 3


def test_reports_an_empty_result_instead_of_returning_nothing() -> None:
    result = search_jobs(reg="ZZ99 ZZZ")
    assert result["count"] == 0
    assert "message" in result


# --------------------------------------------------------------------------
# vehicle_history
# --------------------------------------------------------------------------


def test_finds_the_vehicle() -> None:
    assert vehicle_history("MT66 ZXB")["found"] is True


def test_returns_the_whole_history() -> None:
    assert vehicle_history("MT66 ZXB")["visits"] == 3


def test_newest_visit_first() -> None:
    history = vehicle_history("MT66 ZXB")["history"]
    assert history[0]["opened_date"] >= history[-1]["opened_date"]


def test_surfaces_the_repeat_starting_fault() -> None:
    history = vehicle_history("MT66 ZXB")["history"]
    assert sum("starting fault" in v["description"] for v in history) == 2


def test_includes_technician_notes() -> None:
    assert len(vehicle_history("MT66 ZXB")["notes"]) >= 1


def test_handles_an_unknown_plate() -> None:
    assert vehicle_history("AA00 AAA")["found"] is False


# --------------------------------------------------------------------------
# parts_availability
# --------------------------------------------------------------------------


def test_finds_the_parts_at_or_below_reorder_level() -> None:
    assert parts_availability(only_low_stock=True)["count"] == 6


def test_flags_the_parts_needing_reorder() -> None:
    parts = parts_availability(only_low_stock=True)["parts"]
    assert all(p["needs_reorder"] for p in parts)


def test_searches_parts_by_name() -> None:
    assert parts_availability(query="clutch")["count"] == 1


def test_searches_parts_by_sku() -> None:
    assert parts_availability(query="brk-")["count"] == 2


def test_handles_a_part_that_does_not_exist() -> None:
    assert parts_availability(query="flux capacitor")["count"] == 0


# --------------------------------------------------------------------------
# jobs_blocked_on_parts
# --------------------------------------------------------------------------


def test_finds_the_blocked_jobs() -> None:
    assert jobs_blocked_on_parts()["count"] == 3


def test_every_blocked_job_is_genuinely_short() -> None:
    blocked = jobs_blocked_on_parts()["blocked"]
    assert all(b["in_stock"] < b["qty_needed"] for b in blocked)


def test_computes_the_shortfall() -> None:
    blocked = jobs_blocked_on_parts()["blocked"]
    assert all(b["shortfall"] == b["qty_needed"] - b["in_stock"] for b in blocked)


def test_computes_days_open() -> None:
    blocked = jobs_blocked_on_parts()["blocked"]
    assert all(b["days_open"] >= 0 for b in blocked)


def test_catches_the_job_needing_two_of_a_part_with_one_in_stock() -> None:
    blocked = jobs_blocked_on_parts()["blocked"]
    assert any(b["job_card"] == 1015 and b["shortfall"] == 1 for b in blocked)


# --------------------------------------------------------------------------
# technician_schedule
# --------------------------------------------------------------------------


def test_defaults_to_today() -> None:
    assert technician_schedule()["count"] == 4


def test_totals_the_booked_hours() -> None:
    assert technician_schedule()["booked_hours"] > 0


def test_computes_each_bookings_length() -> None:
    bookings = technician_schedule()["bookings"]
    assert all(b["hours"] > 0 for b in bookings)


def test_accepts_tomorrow() -> None:
    assert technician_schedule(day="tomorrow")["count"] == 3


def test_filters_the_schedule_by_technician() -> None:
    bookings = technician_schedule(technician="Ciara")["bookings"]
    assert bookings and all(b["technician"] == "Ciara Bannon" for b in bookings)


def test_rejects_an_unreadable_date() -> None:
    assert "error" in technician_schedule(day="next Tuesday-ish")


def test_handles_a_day_with_nothing_booked() -> None:
    assert technician_schedule(day="1999-01-01")["count"] == 0


# --------------------------------------------------------------------------
# add_job_note
# --------------------------------------------------------------------------


def test_reports_success() -> None:
    written = add_job_note(1013, "Chased supplier, cat converter due Thursday.")
    assert written["written"] is True


def test_returns_the_job_it_attached_to() -> None:
    written = add_job_note(1013, "Chased supplier.", author="Nick")
    assert written["job_card"] == 1013


def test_echoes_the_vehicle_back() -> None:
    written = add_job_note(1013, "Chased supplier.", author="Nick")
    assert written["vehicle"] == "MT66 ZXB"


def test_the_note_is_actually_persisted() -> None:
    before = len(vehicle_history("MT66 ZXB")["notes"])
    add_job_note(1013, "Chased supplier.", author="Nick")
    assert len(vehicle_history("MT66 ZXB")["notes"]) == before + 1


def test_rejects_an_unknown_job_card() -> None:
    assert add_job_note(9999, "test")["written"] is False


def test_rejects_an_empty_note() -> None:
    assert add_job_note(1013, "   ")["written"] is False


# --------------------------------------------------------------------------
# the read connection really is read-only
# --------------------------------------------------------------------------


def test_a_read_connection_refuses_a_delete() -> None:
    """The guarantee the five read tools rest on, asserted rather than assumed."""
    with pytest.raises(sqlite3.OperationalError):
        connect().execute("DELETE FROM job_cards")
