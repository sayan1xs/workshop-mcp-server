-- Mock schema for a garage management system.
-- Deliberately simplified: enough structure to be realistic, small enough to read in one sitting.

DROP TABLE IF EXISTS job_notes;
DROP TABLE IF EXISTS bookings;
DROP TABLE IF EXISTS job_lines;
DROP TABLE IF EXISTS job_cards;
DROP TABLE IF EXISTS parts;
DROP TABLE IF EXISTS vehicles;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS technicians;

CREATE TABLE customers (
    id      INTEGER PRIMARY KEY,
    name    TEXT NOT NULL,
    phone   TEXT,
    email   TEXT
);

CREATE TABLE vehicles (
    id           INTEGER PRIMARY KEY,
    customer_id  INTEGER NOT NULL REFERENCES customers(id),
    reg          TEXT NOT NULL UNIQUE,   -- UK-style registration plate
    make         TEXT NOT NULL,
    model        TEXT NOT NULL,
    year         INTEGER,
    mileage      INTEGER
);

CREATE TABLE technicians (
    id     INTEGER PRIMARY KEY,
    name   TEXT NOT NULL,
    grade  TEXT NOT NULL            -- apprentice / technician / master
);

CREATE TABLE parts (
    id             INTEGER PRIMARY KEY,
    sku            TEXT NOT NULL UNIQUE,
    name           TEXT NOT NULL,
    in_stock       INTEGER NOT NULL DEFAULT 0,
    reorder_level  INTEGER NOT NULL DEFAULT 0,
    unit_price     REAL NOT NULL,
    supplier       TEXT
);

-- A job card is the central record: one visit of one vehicle to the workshop.
CREATE TABLE job_cards (
    id             INTEGER PRIMARY KEY,
    vehicle_id     INTEGER NOT NULL REFERENCES vehicles(id),
    technician_id  INTEGER REFERENCES technicians(id),
    opened_date    TEXT NOT NULL,       -- ISO date
    closed_date    TEXT,
    status         TEXT NOT NULL,       -- booked | in_progress | waiting_parts | completed | invoiced
    description    TEXT NOT NULL,
    estimate       REAL
);

-- Individual labour or part lines on a job card.
CREATE TABLE job_lines (
    id           INTEGER PRIMARY KEY,
    job_card_id  INTEGER NOT NULL REFERENCES job_cards(id),
    kind         TEXT NOT NULL,          -- labour | part
    description  TEXT NOT NULL,
    part_id      INTEGER REFERENCES parts(id),
    qty          INTEGER NOT NULL DEFAULT 1,
    unit_price   REAL NOT NULL
);

CREATE TABLE bookings (
    id             INTEGER PRIMARY KEY,
    vehicle_id     INTEGER NOT NULL REFERENCES vehicles(id),
    technician_id  INTEGER NOT NULL REFERENCES technicians(id),
    job_card_id    INTEGER REFERENCES job_cards(id),
    bay            TEXT NOT NULL,
    start_time     TEXT NOT NULL,        -- ISO datetime
    end_time       TEXT NOT NULL
);

CREATE TABLE job_notes (
    id           INTEGER PRIMARY KEY,
    job_card_id  INTEGER NOT NULL REFERENCES job_cards(id),
    created_at   TEXT NOT NULL,
    author       TEXT NOT NULL,
    note         TEXT NOT NULL
);

CREATE INDEX idx_jobs_status  ON job_cards(status);
CREATE INDEX idx_jobs_vehicle ON job_cards(vehicle_id);
CREATE INDEX idx_lines_job    ON job_lines(job_card_id);
CREATE INDEX idx_notes_job    ON job_notes(job_card_id);
