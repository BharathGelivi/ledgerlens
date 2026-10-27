# LedgerLens - SUBMITTED October 27, 2026

Target: PayPal AI Hackathon, https://paypalaihackathon.devpost.com/. The owner is registered as a solo participant. Deadline in the signed-in account: November 13, 2026 at 1:30 AM IST.

## Tagline

Trace payment figures back to their evidence before you trust them.

## Inspiration

A dashboard can look convincing while counting a payment twice, using an old pending state, silently dropping an invalid amount, or combining currencies. We wanted to make these failure modes inspectable while teaching the engineer the full data journey.

## What it does

LedgerLens preserves source payloads, counts repeated observations separately, validates records, resolves current states, and withholds conflicting latest values. Its browser workspace offers activity by currency, searchable transactions, source-version traces, quarantine reasons, SQL checks, and run history. Every refresh builds and tests a separate database before publication, preserving the last passing dataset if a build fails.

NVIDIA-powered explanations use aggregate SQL evidence that stays visible for verification. The model cannot execute SQL, alter records, or initiate payments.

## How it was built

Python extracts PayPal sandbox reporting data and validates records. DuckDB stores history and analytical results. Set-based ingestion reduces per-row database-call overhead. dbt models identify ambiguity, current states, and daily activity; tests gate publication. Parquet provides a typed export. FastAPI serves a local responsive HTML/CSS/JavaScript investigation workspace. NVIDIA NIM runs Nemotron 3.5 Lightning remotely.

## Truthful current status

The populated demo is explicitly synthetic and reproducible. Sixteen Python tests, three SQL checks, and HTTP behaviors have passed. Actual sandbox OAuth/reporting works but returned zero transactions; a populated sandbox trace remains a follow-up validation gap. NVIDIA inference has succeeded with the owner's configured account. The entry is submitted at https://devpost.com/software/ledgerlens-o5hndg. The public 2:32 walkthrough is https://youtu.be/GL0EV9CTQqo. Devpost displayed Project submitted and SUBMITTED TO PayPal AI Hackathon.

## Lessons

Repeated observations are different from business transactions. Conflicting latest values should be withheld instead of arbitrarily selected. A failed refresh should not replace a passing dataset. AI explanations need inspectable evidence and review because plausible wording can go beyond what the data establishes.

## Built with

Python, PayPal Transaction Search/OAuth sandbox, JSON, SHA-256, DuckDB, SQL, dbt Core, dbt-duckdb, Parquet/Zstandard, FastAPI, Uvicorn, HTML, CSS, JavaScript, NVIDIA NIM, Nemotron 3.5 Lightning, Windows user-bound credential encryption.

Codex assisted research, implementation, tests, documentation, and submission preparation. Disclose this assistance and review claims before publication.

## Completion checklist

- [x] Check adult India-resident eligibility against published exclusions, subject to other rule restrictions.
- [x] Register as a solo entrant with explicit agreement approval.
- [x] Enable approved sandbox reporting and privately configure existing credentials.
- [x] Verify actual OAuth/reporting and an isolated tested sandbox dataset. Response currently has zero rows.
- [x] Configure the owner's NVIDIA key and verify inference with an accessible model.
- [x] Build/test the interactive investigation workspace.
- [ ] Generate nonzero sandbox activity and verify its reporting through the pipeline after any reporting delay.
- [x] Create and complete the separate Devpost project entry, with screenshots and cover.
- [x] Publish only this project's source, deterministic fixture generator, instructions, and license: https://github.com/BharathGelivi/ledgerlens.
- [x] Verify fresh Windows clone/environment and clean Linux CI installation, tests, and demo build. Public instructions provide local judge access with synthetic data; cloud integrations require their own credentials.
- [x] Publish a 2:32 narrated walkthrough of actual app screenshots, with synthetic-data disclosure: https://youtu.be/GL0EV9CTQqo.
- [x] Save repository/video URLs and confirmed personal answers, accept the authorized rules/terms and submit.
- [x] Write PROJECT_GUIDE.md explaining every tool and the full data journey.
- [x] Stop the local server; ports 8011 and 8012 have no listeners. Earlier build, test and video jobs finished.

## Original demo outline (final video is 2:32)

0:00-0:20: show the payment-data problem. 0:20-0:50: show an explicitly labelled source and, once available, the nonzero sandbox extract. 0:50-1:20: trace a status change and inspect ambiguity. 1:20-1:50: replay input and show stable totals, zero new payloads, passing checks, and retained publication. 1:50-2:20: ask NVIDIA a question and compare the answer to SQL evidence. 2:20-2:40: show the tool chain, measured optimization with its limited scope, and the learning exercise.

Do not claim production accounting, settlement reconciliation, or fraud detection.
