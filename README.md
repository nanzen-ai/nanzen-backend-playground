# Settlements Playground

A small service that works out what our customers still owe us.

---

## The Problem

We invoice customers. They pay into our bank account. Every night the bank
sends us a file of what arrived, this service works out which payment settled
which invoice, and the account team reads the resulting numbers off the
customer page before they get on a call.

**Meridian Health** (`MERID-001`) is one of those customers. Their account
manager, Elena, came to us this week:

> "The outstanding balance we're showing for Meridian is wrong. I took it
> into a renewal call and their finance lead disagreed with me in front of
> her CFO. Can someone look at it?
>
> Also, she wants to know which payment we applied to invoice
> INV-2026-MH-002. Can you get me that?"

That's the task. Work out what's going on, and fix what you think should be
fixed.

---

## How this works

1. **You spend about 90 minutes on this, on your own time.** Not more. We
   grade what's there, and "here's what I found and didn't have time to fix"
   is a perfectly good answer.
2. **You send us a PR** against your copy of this repo, plus a `NOTES.md`
   (half a page, no more).
3. **We talk it through** at the start of your next interview. You'll walk us
   through what you found and we'll ask about the decisions you made.

Use whatever tools you normally use, AI included. We care about what you
found and what you decided, not about how the characters got on the screen.

### What we are not asking for

No authentication, no deployment, no migrations framework, no exhaustive test
suite, no UI. If you find yourself building infrastructure, you've drifted.

### What to put in NOTES.md

- What you found
- What you changed, and why
- What you deliberately left alone
- Anything you'd want to do with more time, and what worries you about it

The notes matter as much as the code.

---

## Setup

```bash
git clone <your-repo-url>
cd nanzen-backend-playground
make install

make reset                          # build the database, load invoices
make run ARGS="import"              # import the bank files, run matching
make run ARGS="report MERID-001"    # print a customer's AR position
```

The database is a SQLite file at the project root. It's disposable, `make
reset` rebuilds it from `data/` at any time.

There's also an HTTP API, which is what the customer page actually calls:

```bash
make serve
# http://localhost:8000/customers/MERID-001/summary
# http://localhost:8000/payments/unmatched
```

---

## The data

`data/` holds the reference data and the nightly bank exports.

| File | What it is |
|---|---|
| `customers.csv` | The three customers |
| `invoices.csv` | Everything we've billed |
| `payments_2026-02-16.csv` | The bank's export on the night of the 16th |
| `payments_2026-02-17.csv` | Same, the 17th |
| `payments_2026-02-18.csv` | Same, the 18th |

The bank sends a rolling window rather than only what's new, so consecutive
files overlap. That's normal and expected.

---

## Project Structure

```
nanzen-backend-playground/
├── README.md
├── pyproject.toml
├── Makefile                   # install, style, test, run, reset, serve
├── data/                      # reference data + nightly bank exports
├── src/
│   └── challenge/
│       ├── store.py           # SQLite schema and connection
│       ├── importer.py        # CSV in
│       ├── matcher.py         # payment -> invoice
│       ├── ledger.py          # accounts receivable
│       ├── api.py             # HTTP API
│       └── runner.py          # CLI
└── tests/
    └── test_matcher.py
```

---

## Commands

```bash
make install                        # install dependencies
make reset                          # rebuild the database from data/
make run ARGS="import"              # import all bank files, then match
make run ARGS="import 2026-02-16"   # import one night only
make run ARGS="report MERID-001"    # AR position for a customer
make serve                          # run the HTTP API on :8000
make test                           # run the tests
make style                          # format and autofix with ruff
```

---

Come with questions. The ones you ask tell us as much as the code you write.
