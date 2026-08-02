# Workshop assistant

An MCP server that lets a language model answer questions about a garage's
workshop — open jobs, vehicle history, parts stock, the day's bookings — by
querying the workshop database directly instead of guessing.

Built as a learning project while working through Anthropic's Model Context
Protocol material. The database is fictional; the point is the interface
between the model and the business system, not the data behind it.

---

## The problem

A service manager starts the day with a handful of questions that are boring
to answer and expensive to get wrong:

- Which jobs are stuck waiting on a part, and how long have they been stuck?
- Has this car been in before for the same fault?
- What does Tuesday look like — is there room to fit someone in?
- Do we have front pads in stock, or does that job need ordering first?

Every one of these is a join across two or three tables. A person answers them
by opening several screens and holding the result in their head. It is exactly
the kind of repeated lookup that gets skipped when the workshop is busy, which
is when getting it wrong costs the most.

An assistant that can read the workshop database answers them in one sentence.

## Why MCP rather than a chatbot with the data pasted in

A language model on its own knows nothing about this workshop, and pasting the
database into a prompt does not scale past a few dozen rows — nor does it stay
current for more than a minute.

MCP is the contract between the two. The server below advertises six named
tools with typed arguments. The model chooses which to call and with what
arguments; the server runs a reviewed SQL query and returns plain structured
data. The model's job is to interpret the question and present the answer. The
database's job is to be correct. Neither has to know how the other works.

## Design decisions

**Narrow tools, not a general `run_sql`.** One tool that executes arbitrary SQL
would be far more flexible and much worse. It would make the model responsible
for correctness against a schema it has only been told about, and it would hand
a language model unrestricted write access to a live business system. Six
specific tools mean each query is written and reviewed once, by a person, and
the model only picks between them.

**Read-only by default.** The five read tools open the database with
`mode=ro`, so a bug in a query cannot modify anything. Only `add_job_note`
opens a writable connection. There is a test that asserts this.

**One write tool, deliberately dull.** `add_job_note` appends a note. It cannot
change a job's status, its parts or its price — those are decisions that need a
person, and an agent that can quietly re-price a job is a liability, not a
feature. Adding a note is genuinely useful (chasing a supplier, recording a
call) and safe to get wrong.

**Empty results say so.** Every tool returns an explicit `message` when nothing
matched. Handed a bare empty list, a model will often fill the silence with a
plausible-sounding job card that does not exist.

**The interesting query is its own tool.** `jobs_blocked_on_parts` could be
assembled by the model from `search_jobs` and `parts_availability`, but that
means three round trips and a join done in the model's head. It is the question
the workshop actually asks every morning, so it gets a tool.

## The tools

| Tool | What it answers |
|---|---|
| `search_jobs` | Job cards, filtered by status, registration plate or technician |
| `vehicle_history` | Every visit for one vehicle, plus technician notes |
| `parts_availability` | Stock levels, with a low-stock filter |
| `jobs_blocked_on_parts` | Open jobs where a required part is short |
| `technician_schedule` | Bookings for a day, with bay, hours and job |
| `add_job_note` | *(write)* Append a note to a job card |

## Running it

Requires Python 3.10+ and the MCP SDK.
The pin exists because 2.0 renamed FastMCP with no deprecation period.

```bash
pip install "mcp[cli]<2"
python seed_data.py      # creates garage.db
python test_tools.py     # 38 checks
```

To use it from Claude Desktop, add this to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "garage-workshop": {
      "command": "python",
      "args": ["/absolute/path/to/garage-agent/server.py"]
    }
  }
}
```

Or from Claude Code:

```bash
claude mcp add garage-workshop -- python /absolute/path/to/garage-agent/server.py
```

## Example session

> **Which jobs are blocked waiting on parts?**
>
> Three jobs are held up:
>
> - **1013** — MT66 ZXB (BMW 320d), MOT failure, catalytic converter. None in
>   stock, on order from Driveline Components. Open 9 days.
> - **1014** — GK17 OPL (Vauxhall Astra), clutch slipping, clutch kit. None in
>   stock. Open 6 days.
> - **1015** — BF15 NRV (Audi A4), timing belt kit. Needs 2, one in stock, so
>   short by one. Open 4 days.
>
> The BMW has been waiting longest, and Derek's note from the day it came in
> says the supplier quoted 7–10 days — that was nine days ago, so it is worth
> chasing today.

> **Has the BMW been in before for this?**
>
> Not for the emissions failure, but it has a repeat history worth knowing
> about. MT66 ZXB has been in three times. Seven months ago it came in for an
> intermittent starting fault and had a battery fitted; three months ago it came
> back with the same symptom and the alternator was replaced. Derek's note on
> the second visit says the charging voltage was low at idle — so the battery
> replacement had treated the symptom rather than the cause.

> **Add a note to 1013 saying I chased the supplier and it's due Thursday.**
>
> Added to job card 1013 (MT66 ZXB, MOT failure — catalytic converter):
> "Chased supplier, catalytic converter due Thursday." Note 6.

## What I would add next

- The parts data has a `supplier` column but nothing uses it. A tool that
  groups outstanding orders by supplier would turn three separate chase-up
  calls into one.
- `technician_schedule` reports booked hours but not free capacity, so it can
  tell you what Tuesday looks like but not whether a job fits.
- No authentication or audit trail. Fine for a local prototype, the first thing
  I would need for anything real — a note written by an agent should record
  that it was written by an agent.

## A note on the data

Every customer, vehicle, registration plate, phone number and email address in
`seed_data.py` is invented for this project. The phone numbers use Ofcom's
reserved `07700 900xxx` range and the email addresses use `example.com`, both
of which exist precisely so that test data cannot collide with a real person.
