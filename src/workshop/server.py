"""Workshop assistant - an MCP server over a garage management database.

The point of this project is the boundary. The language model knows nothing
about this workshop; the database knows nothing about language. MCP is the
contract between them: a small set of named tools with typed arguments that
the model can call, and which return plain data rather than prose.

Every tool here is deliberately narrow. A single "run_sql" tool would be more
flexible and much worse - it would put the model in charge of correctness
against a schema it only knows from a description, and hand it unrestricted
write access to a live business system. Narrow tools mean the queries are
written and reviewed once, by a person, and the model only chooses between
them.

    uv run workshop-mcp
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from mcp.server.fastmcp import FastMCP

from workshop.db import connect, rows

mcp = FastMCP("garage-workshop")

# Statuses that mean the job is still live in the workshop.
OPEN_STATUSES = ("booked", "in_progress", "waiting_parts")


# --------------------------------------------------------------------------
# read tools
# --------------------------------------------------------------------------
@mcp.tool()
def search_jobs(
    status: str | None = None,
    reg: str | None = None,
    technician: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Search job cards in the workshop.

    Args:
        status: One of booked, in_progress, waiting_parts, completed, invoiced.
                Use "open" for anything not yet finished.
        reg: Registration plate, full or partial (e.g. "LM19" or "LM19 KTZ").
        technician: Technician name, full or partial.
        limit: Maximum number of job cards to return.
    """
    where: list[str] = []
    params: list[Any] = []

    if status:
        key = status.strip().lower()
        if key == "open":
            where.append(f"j.status IN ({','.join('?' * len(OPEN_STATUSES))})")
            params.extend(OPEN_STATUSES)
        else:
            where.append("j.status = ?")
            params.append(key)
    if reg:
        where.append("REPLACE(v.reg,' ','') LIKE ?")
        params.append(f"%{reg.replace(' ', '').upper()}%")
    if technician:
        where.append("t.name LIKE ?")
        params.append(f"%{technician}%")

    clause = f"WHERE {' AND '.join(where)}" if where else ""
    params.append(limit)

    jobs = rows(
        f"""
        SELECT j.id AS job_card, j.status, j.opened_date, j.description,
               j.estimate, v.reg, v.make, v.model, c.name AS customer,
               COALESCE(t.name, 'unassigned') AS technician
        FROM job_cards j
        JOIN vehicles v    ON v.id = j.vehicle_id
        JOIN customers c   ON c.id = v.customer_id
        LEFT JOIN technicians t ON t.id = j.technician_id
        {clause}
        ORDER BY j.opened_date DESC
        LIMIT ?
        """,
        tuple(params),
    )

    # Say plainly when nothing matched. Left to guess, a model will often
    # invent a plausible job card rather than report an empty result.
    if not jobs:
        return {
            "count": 0,
            "jobs": [],
            "message": "No job cards matched those filters.",
        }
    return {"count": len(jobs), "jobs": jobs}


@mcp.tool()
def vehicle_history(reg: str) -> dict[str, Any]:
    """Full service history for one vehicle, newest first.

    Use this to answer questions like "has this car been in before for the
    same fault?" - repeat visits for one symptom are the useful signal.

    Args:
        reg: Registration plate, full or partial.
    """
    needle = f"%{reg.replace(' ', '').upper()}%"
    vehicles = rows(
        """
        SELECT v.id, v.reg, v.make, v.model, v.year, v.mileage,
               c.name AS customer, c.phone
        FROM vehicles v
        JOIN customers c ON c.id = v.customer_id
        WHERE REPLACE(v.reg,' ','') LIKE ?
        """,
        (needle,),
    )

    if not vehicles:
        return {"found": False, "message": f"No vehicle on file matching '{reg}'."}
    if len(vehicles) > 1:
        return {
            "found": False,
            "message": "That matches more than one vehicle. Be more specific.",
            "candidates": [v["reg"] for v in vehicles],
        }

    vehicle = vehicles[0]
    history = rows(
        """
        SELECT j.id AS job_card, j.opened_date, j.closed_date, j.status,
               j.description, j.estimate,
               COALESCE(t.name,'unassigned') AS technician
        FROM job_cards j
        LEFT JOIN technicians t ON t.id = j.technician_id
        WHERE j.vehicle_id = ?
        ORDER BY j.opened_date DESC
        """,
        (vehicle["id"],),
    )
    notes = rows(
        """
        SELECT n.job_card_id, n.created_at, n.author, n.note
        FROM job_notes n
        JOIN job_cards j ON j.id = n.job_card_id
        WHERE j.vehicle_id = ?
        ORDER BY n.created_at DESC
        """,
        (vehicle["id"],),
    )

    return {
        "found": True,
        "vehicle": vehicle,
        "visits": len(history),
        "history": history,
        "notes": notes,
    }


@mcp.tool()
def parts_availability(
    query: str | None = None, only_low_stock: bool = False
) -> dict[str, Any]:
    """Look up parts stock.

    Args:
        query: Part name or SKU, full or partial. Omit to list everything.
        only_low_stock: If true, return only parts at or below reorder level.
    """
    where, params = [], []
    if query:
        where.append("(name LIKE ? OR sku LIKE ?)")
        params.extend([f"%{query}%", f"%{query.upper()}%"])
    if only_low_stock:
        where.append("in_stock <= reorder_level")

    clause = f"WHERE {' AND '.join(where)}" if where else ""
    parts = rows(
        f"""
        SELECT sku, name, in_stock, reorder_level, unit_price, supplier
        FROM parts {clause}
        ORDER BY (in_stock <= reorder_level) DESC, name
        """,
        tuple(params),
    )

    if not parts:
        return {"count": 0, "parts": [], "message": "No parts matched that search."}

    for p in parts:
        p["needs_reorder"] = p["in_stock"] <= p["reorder_level"]
    return {"count": len(parts), "parts": parts}


@mcp.tool()
def jobs_blocked_on_parts() -> dict[str, Any]:
    """Open job cards that cannot proceed because a required part is short.

    This is the question a service manager actually asks each morning, and it
    is the reason the assistant is worth having: answering it by hand means
    cross-referencing every open job against the stock list.
    """
    blocked = rows(
        f"""
        SELECT j.id AS job_card, j.status, j.opened_date, j.description,
               v.reg, v.make, v.model, c.name AS customer,
               p.sku, p.name AS part, l.qty AS qty_needed,
               p.in_stock, p.supplier
        FROM job_cards j
        JOIN vehicles v  ON v.id = j.vehicle_id
        JOIN customers c ON c.id = v.customer_id
        JOIN job_lines l ON l.job_card_id = j.id AND l.kind = 'part'
        JOIN parts p     ON p.id = l.part_id
        WHERE j.status IN ({",".join("?" * len(OPEN_STATUSES))})
          AND p.in_stock < l.qty
        ORDER BY j.opened_date
        """,
        OPEN_STATUSES,
    )

    if not blocked:
        return {
            "count": 0,
            "blocked": [],
            "message": "Nothing is currently held up waiting for parts.",
        }

    for b in blocked:
        b["shortfall"] = b["qty_needed"] - b["in_stock"]
        b["days_open"] = (date.today() - date.fromisoformat(b["opened_date"])).days
    return {"count": len(blocked), "blocked": blocked}


@mcp.tool()
def technician_schedule(
    day: str | None = None, technician: str | None = None
) -> dict[str, Any]:
    """Workshop bookings for a given day.

    Args:
        day: ISO date (YYYY-MM-DD), or "today" / "tomorrow". Defaults to today.
        technician: Technician name, full or partial. Omit for the whole workshop.
    """
    if day is None or day.strip().lower() == "today":
        target = date.today()
    elif day.strip().lower() == "tomorrow":
        target = date.fromordinal(date.today().toordinal() + 1)
    else:
        try:
            target = date.fromisoformat(day.strip())
        except ValueError:
            return {
                "error": f"Could not read '{day}' as a date. "
                "Use YYYY-MM-DD, 'today' or 'tomorrow'."
            }

    where = ["DATE(b.start_time) = ?"]
    params: list[Any] = [target.isoformat()]
    if technician:
        where.append("t.name LIKE ?")
        params.append(f"%{technician}%")

    bookings = rows(
        f"""
        SELECT b.start_time, b.end_time, b.bay, t.name AS technician,
               t.grade, v.reg, v.make, v.model,
               b.job_card_id AS job_card,
               COALESCE(j.description,'(no job card)') AS work,
               COALESCE(j.status,'-') AS status
        FROM bookings b
        JOIN technicians t ON t.id = b.technician_id
        JOIN vehicles v    ON v.id = b.vehicle_id
        LEFT JOIN job_cards j ON j.id = b.job_card_id
        WHERE {" AND ".join(where)}
        ORDER BY b.start_time, b.bay
        """,
        tuple(params),
    )

    if not bookings:
        return {
            "day": target.isoformat(),
            "count": 0,
            "bookings": [],
            "message": f"Nothing booked in for {target.isoformat()}.",
        }

    hours = 0.0
    for b in bookings:
        span = datetime.fromisoformat(b["end_time"]) - datetime.fromisoformat(
            b["start_time"]
        )
        b["hours"] = round(span.total_seconds() / 3600, 2)
        hours += b["hours"]

    return {
        "day": target.isoformat(),
        "count": len(bookings),
        "booked_hours": round(hours, 2),
        "bookings": bookings,
    }


# --------------------------------------------------------------------------
# write tool
# --------------------------------------------------------------------------
@mcp.tool()
def add_job_note(
    job_card: int, note: str, author: str = "Workshop assistant"
) -> dict[str, Any]:
    """Add a note to a job card.

    The only tool here that changes anything. It is narrow on purpose: it can
    append a note and nothing else. It cannot alter a job's status, its parts
    or its price - those are decisions that need a person.

    Args:
        job_card: The job card ID to attach the note to.
        note: The text of the note.
        author: Who the note is from.
    """
    text = note.strip()
    if not text:
        return {"written": False, "error": "The note is empty."}

    con = connect(write=True)
    try:
        job = con.execute(
            """
            SELECT j.id, j.status, j.description, v.reg
            FROM job_cards j JOIN vehicles v ON v.id = j.vehicle_id
            WHERE j.id = ?
            """,
            (job_card,),
        ).fetchone()

        # Check the job exists before writing, so a mistyped ID fails loudly
        # instead of leaving an orphaned note nobody will ever read.
        if job is None:
            return {"written": False, "error": f"No job card {job_card} exists."}

        cur = con.execute(
            "INSERT INTO job_notes (job_card_id, created_at, author, note) "
            "VALUES (?,?,?,?)",
            (job_card, date.today().isoformat(), author, text),
        )
        con.commit()
        note_id = cur.lastrowid
    finally:
        con.close()

    return {
        "written": True,
        "note_id": note_id,
        "job_card": job_card,
        "vehicle": job["reg"],
        "job": job["description"],
        "status": job["status"],
        "author": author,
        "note": text,
    }


def main() -> None:
    """Entry point for the `workshop-mcp` console script."""
    mcp.run()


if __name__ == "__main__":
    main()
