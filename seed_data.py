"""Create garage.db and fill it with fictional workshop data.

Everything in here is invented. The names, registration plates, phone numbers
and email addresses do not belong to anyone. Run this once before starting the
MCP server:

    python seed_data.py
"""

import sqlite3
import os
from datetime import date, datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "garage.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")

TODAY = date.today()


def d(offset_days: int) -> str:
    """An ISO date `offset_days` from today. Negative is in the past."""
    return (TODAY + timedelta(days=offset_days)).isoformat()


def dt(offset_days: int, hour: int, minute: int = 0) -> str:
    """An ISO datetime `offset_days` from today at the given time."""
    return datetime.combine(
        TODAY + timedelta(days=offset_days), datetime.min.time()
    ).replace(hour=hour, minute=minute).isoformat(timespec="minutes")


CUSTOMERS = [
    (1, "Alan Petrie", "07700 900112", "alan.petrie@example.com"),
    (2, "Marta Kalnina", "07700 900318", "m.kalnina@example.com"),
    (3, "Dermot Cahill", "07700 900447", "dcahill@example.com"),
    (4, "Priya Raman", "07700 900556", "priya.raman@example.com"),
    (5, "Gordon Blaikie", "07700 900673", "g.blaikie@example.com"),
    (6, "Sofia Ferreira", "07700 900781", "sofia.f@example.com"),
    (7, "Tom Whitworth", "07700 900894", "t.whitworth@example.com"),
    (8, "Hannah Doyle", "07700 900927", "hannah.doyle@example.com"),
    (9, "Ravi Chandra", "07700 900035", "r.chandra@example.com"),
    (10, "Elaine Murchison", "07700 900164", "elaine.m@example.com"),
]

VEHICLES = [
    (1, 1, "LM19 KTZ", "Ford", "Focus", 2019, 62400),
    (2, 2, "SP68 HRD", "Volkswagen", "Golf", 2018, 88150),
    (3, 3, "YB21 WNC", "Toyota", "Corolla", 2021, 31200),
    (4, 4, "GK17 OPL", "Vauxhall", "Astra", 2017, 104800),
    (5, 5, "RA70 DVM", "Nissan", "Qashqai", 2020, 45300),
    (6, 6, "MT66 ZXB", "BMW", "320d", 2016, 132900),
    (7, 7, "CE20 FJU", "Skoda", "Octavia", 2020, 58700),
    (8, 8, "WD18 LSA", "Renault", "Clio", 2018, 71500),
    (9, 9, "HN22 TQE", "Kia", "Sportage", 2022, 24100),
    (10, 10, "BF15 NRV", "Audi", "A4", 2015, 148600),
    (11, 1, "PL19 CMD", "Ford", "Transit", 2019, 96200),
    (12, 4, "JD21 XKW", "Hyundai", "i30", 2021, 28900),
]

TECHNICIANS = [
    (1, "Derek Lowrie", "master"),
    (2, "Ciara Bannon", "technician"),
    (3, "Stefan Mihai", "technician"),
    (4, "Owen Pritchard", "apprentice"),
]

# in_stock deliberately below reorder_level for a few items so that
# jobs_blocked_on_parts() has something real to find.
PARTS = [
    (1, "BRK-PAD-F-014", "Front brake pads (set)", 12, 4, 34.50, "Eurotrade Motor Factors"),
    (2, "BRK-DSC-F-207", "Front brake discs (pair)", 3, 4, 78.00, "Eurotrade Motor Factors"),
    (3, "OIL-5W30-5L", "Engine oil 5W-30, 5L", 22, 6, 29.95, "Eurotrade Motor Factors"),
    (4, "FLT-OIL-311", "Oil filter", 18, 8, 7.20, "Eurotrade Motor Factors"),
    (5, "FLT-AIR-155", "Air filter", 9, 5, 11.40, "Eurotrade Motor Factors"),
    (6, "FLT-CAB-092", "Cabin filter", 6, 5, 13.75, "Eurotrade Motor Factors"),
    (7, "BAT-063-STD", "Battery, type 063", 4, 2, 92.00, "Northern Battery Supply"),
    (8, "CLU-KIT-448", "Clutch kit", 0, 1, 289.00, "Driveline Components Ltd"),
    (9, "ALT-1120-RM", "Alternator (remanufactured)", 1, 1, 214.50, "Driveline Components Ltd"),
    (10, "SUS-COIL-R-77", "Rear coil spring", 2, 2, 46.80, "Eurotrade Motor Factors"),
    (11, "EXH-CAT-503", "Catalytic converter", 0, 1, 412.00, "Driveline Components Ltd"),
    (12, "GLW-PLG-4X", "Glow plugs (set of 4)", 5, 2, 58.40, "Eurotrade Motor Factors"),
    (13, "TYR-205-55-16", "Tyre 205/55 R16", 8, 4, 74.00, "Kirkgate Tyres"),
    (14, "WIP-BLD-24", "Wiper blade 24in", 20, 6, 9.90, "Eurotrade Motor Factors"),
    (15, "COOL-G12-5L", "Coolant G12, 5L", 7, 3, 24.30, "Eurotrade Motor Factors"),
    (16, "TIM-BLT-KIT-19", "Timing belt kit", 1, 2, 176.00, "Driveline Components Ltd"),
]

# (id, vehicle, technician, opened, closed, status, description, estimate)
JOB_CARDS = [
    # --- closed history -------------------------------------------------
    (1001, 1, 1, d(-320), d(-319), "invoiced", "Annual service and MOT preparation", 210.00),
    (1002, 2, 2, d(-280), d(-279), "invoiced", "Front brake pads and discs replaced", 265.00),
    (1003, 4, 1, d(-240), d(-238), "invoiced", "Clutch replacement", 640.00),
    (1004, 6, 3, d(-210), d(-209), "invoiced", "Intermittent starting fault - battery replaced", 145.00),
    (1005, 3, 2, d(-180), d(-180), "invoiced", "Oil and filter service", 96.00),
    (1006, 6, 1, d(-96), d(-94), "invoiced", "Intermittent starting fault - alternator replaced", 318.00),
    (1007, 8, 4, d(-88), d(-88), "invoiced", "Wiper blades and bulb replacement", 42.00),
    (1008, 10, 1, d(-64), d(-61), "invoiced", "Timing belt and water pump", 495.00),
    (1009, 5, 3, d(-45), d(-44), "invoiced", "Rear suspension knock - coil spring replaced", 178.00),
    (1010, 7, 2, d(-30), d(-29), "invoiced", "Full service", 205.00),
    (1011, 9, 4, d(-21), d(-21), "completed", "Tyre replacement x2 and alignment check", 195.00),
    (1012, 12, 3, d(-14), d(-13), "invoiced", "Cabin filter and air filter replacement", 68.00),
    # --- open work ------------------------------------------------------
    (1013, 6, 1, d(-9), None, "waiting_parts", "MOT failure - catalytic converter to replace", 560.00),
    (1014, 4, 2, d(-6), None, "waiting_parts", "Clutch slipping under load - clutch kit required", 690.00),
    (1015, 10, 3, d(-4), None, "waiting_parts", "Timing belt due by mileage - kit on order", 520.00),
    (1016, 2, 2, d(-3), None, "in_progress", "Front discs worn, pads at 2mm", 240.00),
    (1017, 11, 1, d(-2), None, "in_progress", "Glow plug fault, poor cold starting", 190.00),
    (1018, 3, 4, d(-1), None, "in_progress", "Interim service", 110.00),
    (1019, 1, 2, d(0), None, "booked", "Annual service and MOT", 220.00),
    (1020, 5, 3, d(1), None, "booked", "Brake fluid change and inspection", 85.00),
    (1021, 7, 4, d(1), None, "booked", "Air conditioning not cooling - diagnostic", 60.00),
    (1022, 8, 2, d(2), None, "booked", "Battery warning light investigation", 75.00),
    (1023, 9, 1, d(3), None, "booked", "First annual service", 165.00),
    (1024, 12, 3, d(4), None, "booked", "Front brake pads", 130.00),
]

# (job_card_id, kind, description, part_id, qty, unit_price)
JOB_LINES = [
    (1002, "part", "Front brake pads (set)", 1, 1, 34.50),
    (1002, "part", "Front brake discs (pair)", 2, 1, 78.00),
    (1002, "labour", "Brake overhaul, 2.0 hrs", None, 1, 130.00),
    (1003, "part", "Clutch kit", 8, 1, 289.00),
    (1003, "labour", "Clutch replacement, 5.0 hrs", None, 1, 325.00),
    (1004, "part", "Battery, type 063", 7, 1, 92.00),
    (1006, "part", "Alternator (remanufactured)", 9, 1, 214.50),
    (1008, "part", "Timing belt kit", 16, 1, 176.00),
    (1009, "part", "Rear coil spring", 10, 1, 46.80),
    (1011, "part", "Tyre 205/55 R16", 13, 2, 74.00),
    (1012, "part", "Cabin filter", 6, 1, 13.75),
    (1012, "part", "Air filter", 5, 1, 11.40),
    # open jobs
    (1013, "part", "Catalytic converter", 11, 1, 412.00),
    (1013, "labour", "Exhaust work, 2.5 hrs", None, 1, 148.00),
    (1014, "part", "Clutch kit", 8, 1, 289.00),
    (1014, "labour", "Clutch replacement, 5.5 hrs", None, 1, 357.50),
    (1015, "part", "Timing belt kit", 16, 2, 176.00),
    (1016, "part", "Front brake pads (set)", 1, 1, 34.50),
    (1016, "part", "Front brake discs (pair)", 2, 1, 78.00),
    (1017, "part", "Glow plugs (set of 4)", 12, 1, 58.40),
    (1018, "part", "Engine oil 5W-30, 5L", 3, 1, 29.95),
    (1018, "part", "Oil filter", 4, 1, 7.20),
    (1019, "part", "Engine oil 5W-30, 5L", 3, 1, 29.95),
    (1019, "part", "Oil filter", 4, 1, 7.20),
    (1024, "part", "Front brake pads (set)", 1, 1, 34.50),
]

BOOKINGS = [
    (1, 1, 2, 1019, "Bay 1", dt(0, 8, 30), dt(0, 11, 0)),
    (2, 3, 4, 1018, "Bay 3", dt(0, 9, 0), dt(0, 12, 0)),
    (3, 2, 2, 1016, "Bay 1", dt(0, 13, 0), dt(0, 16, 30)),
    (4, 11, 1, 1017, "Bay 2", dt(0, 8, 0), dt(0, 12, 30)),
    (5, 5, 3, 1020, "Bay 3", dt(1, 8, 30), dt(1, 10, 0)),
    (6, 7, 4, 1021, "Bay 4", dt(1, 10, 30), dt(1, 12, 0)),
    (7, 6, 1, 1013, "Bay 2", dt(1, 13, 0), dt(1, 17, 0)),
    (8, 8, 2, 1022, "Bay 1", dt(2, 9, 0), dt(2, 10, 30)),
    (9, 4, 2, 1014, "Bay 1", dt(2, 11, 0), dt(2, 17, 0)),
    (10, 9, 1, 1023, "Bay 2", dt(3, 8, 30), dt(3, 11, 0)),
    (11, 10, 3, 1015, "Bay 3", dt(3, 9, 0), dt(3, 16, 0)),
    (12, 12, 3, 1024, "Bay 3", dt(4, 8, 30), dt(4, 10, 0)),
]

JOB_NOTES = [
    (1, 1006, d(-96), "Derek Lowrie",
     "Customer reports same symptom as the battery job earlier this year. "
     "Charging voltage low at idle, alternator output intermittent."),
    (2, 1013, d(-9), "Derek Lowrie",
     "MOT failed on emissions. Cat converter on order, supplier quoted 7-10 days."),
    (3, 1014, d(-6), "Ciara Bannon",
     "Confirmed slip on road test in 3rd and 4th. Clutch kit not in stock."),
    (4, 1015, d(-4), "Stefan Mihai",
     "Belt due by mileage rather than fault. Customer happy to wait for the kit."),
    (5, 1016, d(-3), "Ciara Bannon",
     "Discs lipped, pads at 2mm. Parts in stock, no delay expected."),
]


def main() -> None:
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    con = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH, "r", encoding="utf-8") as fh:
        con.executescript(fh.read())

    con.executemany("INSERT INTO customers VALUES (?,?,?,?)", CUSTOMERS)
    con.executemany("INSERT INTO vehicles VALUES (?,?,?,?,?,?,?)", VEHICLES)
    con.executemany("INSERT INTO technicians VALUES (?,?,?)", TECHNICIANS)
    con.executemany("INSERT INTO parts VALUES (?,?,?,?,?,?,?)", PARTS)
    con.executemany(
        "INSERT INTO job_cards (id, vehicle_id, technician_id, opened_date, "
        "closed_date, status, description, estimate) VALUES (?,?,?,?,?,?,?,?)",
        JOB_CARDS,
    )
    con.executemany(
        "INSERT INTO job_lines (job_card_id, kind, description, part_id, qty, unit_price) "
        "VALUES (?,?,?,?,?,?)",
        JOB_LINES,
    )
    con.executemany("INSERT INTO bookings VALUES (?,?,?,?,?,?,?)", BOOKINGS)
    con.executemany("INSERT INTO job_notes VALUES (?,?,?,?,?)", JOB_NOTES)

    con.commit()

    counts = {
        table: con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in (
            "customers", "vehicles", "technicians", "parts",
            "job_cards", "job_lines", "bookings", "job_notes",
        )
    }
    con.close()

    print(f"Created {DB_PATH}")
    for table, n in counts.items():
        print(f"  {table:<14} {n:>4} rows")


if __name__ == "__main__":
    main()
