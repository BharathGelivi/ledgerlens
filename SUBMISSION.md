# LedgerLens - entry draft, NOT SUBMITTED

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

The populated demo is explicitly synthetic and reproducible. Sixteen Python tests, three SQL checks, and HTTP behaviors have passed. Actual sandbox OAuth/reporting works but returned zero transactions; a populated sandbox trace is still required. NVIDIA inference has succeeded with the owner's configured account. Registration is complete; no final project entry or video has been submitted.

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
- [ ] Create the separate Devpost project draft; its verification service stalled during the attempt.
- [x] Publish only this project's source, synthetic fixture, instructions, and license: https://github.com/BharathGelivi/ledgerlens.
- [x] Verify fresh Windows clone/environment and clean Linux CI installation, tests, and demo build. Public instructions provide local judge access with synthetic data; cloud integrations require their own credentials.
- [ ] Record a working demo under three minutes and upload publicly to YouTube.
- [ ] Add the actual repository/video URLs, review the finished entry, and submit.

## Suggested 2:40 demo

0:00-0:20: show the payment-data problem. 0:20-0:50: show an explicitly labelled source and, once available, the nonzero sandbox extract. 0:50-1:20: trace a status change and inspect ambiguity. 1:20-1:50: replay input and show stable totals, zero new payloads, passing checks, and retained publication. 1:50-2:20: ask NVIDIA a question and compare the answer to SQL evidence. 2:20-2:40: show the tool chain, measured optimization with its limited scope, and the learning exercise.

Do not claim production accounting, settlement reconciliation, or fraud detection.
