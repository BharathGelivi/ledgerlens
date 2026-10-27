# Learn LedgerLens end to end

LedgerLens answers a practical question: **can you trace a payment figure back to the observations that produced it?** A source can repeat an observation, change a status, send malformed money, or contradict itself. The project preserves those facts before producing a dashboard or asking AI to explain them.

Source: https://github.com/BharathGelivi/ledgerlens

Walkthrough: https://youtu.be/GL0EV9CTQqo

## The complete journey

```text
PayPal sandbox --OAuth / paginated HTTPS--> JSON snapshot
Synthetic generator ---------------------> JSON snapshot (separate dataset)
  -> Python contract + SHA-256 fingerprints
  -> DuckDB: raw_records + record_sightings
              | valid_records       | quarantine + reason
              v
  -> dbt: conflicts -> payments -> daily_activity
  -> SQL checks -> compressed Parquet + run manifest
  -> atomic active.json publication
  -> FastAPI -> browser investigation workspace
               -> aggregate evidence -> NVIDIA NIM -> reviewed explanation
```

The demo and sandbox have separate data folders. They are not merged. The populated walkthrough is synthetic; the real sandbox authentication and reporting connection works but currently returns zero transactions.

## What every tool contributes

| Tool or format | How it works here | Why it belongs |
|---|---|---|
| Python | Runs collection, validation, orchestration, APIs and tests | One readable language for boundaries and control flow |
| Virtual environment + pinned requirements | Isolates installed libraries and their versions | Reproduces the environment without changing global packages |
| PayPal OAuth | Exchanges configured application credentials for a temporary access token | Authenticates the approved read-only reporting integration |
| Transaction Search / HTTPS | Reads reporting pages for an explicit time window | Provides actual provider observations; it does not initiate payments |
| JSON | Stores the source snapshot and individual source payloads | Preserves evidence before interpretation |
| SHA-256 | Derives a fingerprint from each serialized payload | Detects repeated identical observations; it is not encryption or a business transaction ID |
| Decimal / UTC | Validates exact base-10 amounts and normalizes aware timestamps | Avoids binary floating-point money errors and timezone ambiguity |
| DuckDB | Embedded analytical SQL database reading local versioned files | Executes grouping/window queries without a separate database server |
| SQL transactions and batch insertion | Commits a group of changes together; inserts JSON batches using set operations | Prevents partial ingestion and reduces per-row client/database overhead |
| dbt Core + dbt-duckdb | Resolves model dependencies through ref(), builds SQL tables and runs checks | Makes transformation order and quality gates explicit |
| Window functions | Finds the greatest update time within each transaction/event key | Resolves current state while retaining source history |
| Parquet + Zstandard | Writes typed, compressed columnar analytical output | Supports efficient downstream analytical reads and portable exports |
| Atomic file replacement | Replaces the publication pointer only after success | Readers retain a passing dataset when a refresh fails |
| FastAPI + Uvicorn | Defines HTTP routes and runs the local web server | Gives the browser bounded, validated access to published results |
| HTML / CSS / JavaScript | Displays charts, filters, evidence and trace views; requests the API | Makes engineering decisions inspectable without frontend build tooling |
| NVIDIA NIM / Nemotron | Runs remote model inference on aggregate evidence | Explains computed facts without downloading model weights to the laptop |
| Windows DPAPI | Encrypts local credentials for the Windows user | Keeps keys out of source and makes copied encrypted files unusable to other users |
| unittest + SQL checks + HTTP checker | Exercises boundary cases, model invariants and actual app behavior | Checks different layers rather than trusting a screenshot |
| GitHub + Actions | Publishes MIT source and runs a clean Linux verification job | Lets reviewers reproduce the result independently |

## Follow one payment through the system

1. Run generate_demo.py. Its deterministic source includes DEMO-029000000038, event T0006, with pending and completed observations for EUR 19.49.
2. pipeline.py fingerprints each payload. Different states have different payload hashes. Repeated copies share a hash, but record_sightings retains their occurrence counts for that run.
3. normalize() checks required fields, event-code shape, allowed status, currency shape, timestamps and decimal range. Valid observations enter valid_records. Invalid observations remain inspectable through raw_records and quarantine.
4. The dbt payments model chooses the latest unambiguous update for that transaction/event key. The pending version remains in history; it is not counted as a second current payment.
5. daily_activity groups the current states by initiation date in UTC and currency. Completed signed amounts are summed only for status S. A current state grouped by initiation date is not a historical daily status snapshot or a settlement report.
6. SQL checks must pass before the newly built database becomes active. The browser's trace view shows the preserved transition and source fingerprints.

For DEMO-000000000000, the latest observations disagree: USD 999.99 versus USD 9.19 at the same update time. conflicts detects the disagreement. payments excludes the key, and the issue view exposes both alternatives. Picking a row arbitrarily would manufacture certainty.

## Understand the numbers

The deterministic input has 1,444 observations, 1,264 distinct payloads, 1,256 valid historical versions, eight quarantined payloads and one ambiguous latest key. The current model contains 1,199 records after ambiguity is withheld. These counts describe different grains: an occurrence, a payload, a version and a current transaction/event are not interchangeable.

Replay the same source. New distinct payloads should be zero and current totals should remain stable. Observations increase because the system really saw the source again. This is idempotent ingestion, not deletion of the audit history.

Currencies stay separate. Adding USD and EUR produces no meaningful money total without an explicit rate source, rate date, rounding policy and accounting purpose. Currency validation currently checks a three-letter shape, not the complete provider catalogue.

## What happens during a refresh

The pipeline takes a writer lock, creates a new run version, ingests the snapshot, executes dbt, runs three SQL checks, exports Parquet, writes run evidence and finally replaces active.json. Each run records source hashes, counts, timings and outcome. Failed work does not publish. Readers use read-only connections to an immutable published database, which also avoids a Windows refresh/copy race discovered during testing.

The three SQL invariants are unique current keys, no ambiguous keys in payments, and agreement between summary amounts and detail. Raw ingestion is incremental and idempotent; the dbt tables rebuild. Retained run copies trade disk space for reproducibility. Never remove the active version while serving it.

## How the browser and AI fit together

serve.py starts Uvicorn on 127.0.0.1:8011. FastAPI provides /workspace, /activity, /quality, /transactions, /trace, /issues, /export, /replay and /investigate. Queries use parameters rather than interpolating search text into SQL. Inputs and result sizes are bounded. Host, origin and mutation-header checks protect the local workflow. This is a local application, not production multi-user authentication.

The browser has four sections. Overview summarizes activity by currency. Transactions filters current records and opens history. Pipeline & quality exposes rejected/ambiguous records, checks and run history. How it works explains the flow and offers a replay exercise.

For an investigation, SQL computes aggregate evidence across all published current records by currency plus status/quality counts and rejection reasons. briefing.py sends that evidence and the question to the fixed NVIDIA endpoint. The verified model is nvidia/nemotron-3.5-lightning-30b-a3b, with thinking disabled and a 1,200-output-token ceiling. Incomplete responses are rejected. The model receives no transaction IDs, payer details, raw payloads, credentials, SQL execution tool or payment tool. Evidence remains visible so you can challenge the explanation. A plausible answer can still speculate; human review is required.

## Run and learn locally

In PowerShell from the repository folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe generate_demo.py
.\.venv\Scripts\python.exe pipeline.py --input fixtures\demo.json --dataset demo
.\.venv\Scripts\python.exe serve.py --dataset demo
```

Open http://127.0.0.1:8011/. Stop the server with Ctrl+C. Synthetic exploration needs no cloud credentials. configure_ai.py accepts a key through a masked local prompt; never paste it into chat or source. The encrypted credential files and datasets are ignored. Other users must configure their own keys. Collection instructions and reporting date-window restrictions are in README.md.

Read code in this order: generate_demo.py -> collect_sandbox.py -> pipeline.py normalize()/ingest()/run orchestration -> models/conflicts.sql -> models/payments.sql -> models/daily_activity.sql -> tests_sql -> api.py -> web/app.js -> briefing.py -> credentials.py. Then read test_pipeline.py, test_ai.py and verify_workspace.py to see which promises are actually checked.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s . -p test_*.py -v
.\.venv\Scripts\python.exe verify_workspace.py
.\.venv\Scripts\python.exe benchmark.py
```

The HTTP checker expects the deterministic demo server on port 8011 and exercises replay. It does not make a paid AI request. Sixteen Python tests, three SQL checks, the HTTP flow, a fresh Windows environment and clean Linux CI have passed.

## Optimization you can defend

The original ingestion issued database operations for individual rows. The optimized path validates in Python, batches values and performs set-based database inserts in one transaction. A same-process benchmark with fresh in-memory databases and identical 1,444-observation input measured 21.2549 seconds versus 0.0515 seconds and asserted identical normalized/quarantine output. This is one ingestion-only microbenchmark; it excludes disk, dbt and collection. The whole application is not claimed to be hundreds of times faster.

DuckDB uses one worker, a 512 MB buffer setting and a 1 GB spill bound. These do not cap total process RAM. Whole-process peak RAM was not measured. Remote inference avoids local model memory/GPU load. A normal demo build was about 7.7 seconds; cold environment startup can be substantially slower.

Kafka, Spark, Airflow and a distributed warehouse were omitted because this bounded single-account batch workflow does not yet need streams, a cluster or a scheduler. Introduce scheduling when recurring extraction is needed; incremental dbt after measured rebuild costs; a multi-user service/database after measured concurrency demands. Adding services without that need would add operational failure modes without improving this result.

## Exercises that prove understanding

1. Predict replay counts, replay, and explain why observations grow while current totals do not.
2. Trace the pending-to-completed example. Identify source time versus ingestion time.
3. Inspect the ambiguous key. Explain why excluding it is safer than sorting by hash to select a monetary value.
4. Find a quarantine reason and read the validator that produces it. Use a copied fixture for experiments; do not edit raw evidence in place.
5. Read a run's dbt manifest and run_results alongside ref() calls. Explain the dependency order and publication gate.
6. Compare every number in an AI response to its evidence. Mark causes the data does not establish as hypotheses.

## Honest boundaries and next work

This is a tested hackathon project, not production accounting, revenue recognition, settlement reconciliation, FX conversion or fraud detection. The reporting collector is bounded to 10,000 records/10 MB; pipeline snapshots are bounded to 50 MB. One sandbox account is assumed per dataset. Multi-merchant/event key semantics need further validation. Retention consumes disk; hard crashes can leave a lock that should only be removed after confirming no writer remains. OneDrive sync may lock databases; an unsynced working copy can help.

The most useful next verification is nonzero PayPal sandbox activity flowing through delayed reporting. No populated real-payment trace is claimed. Then measure larger inputs and peak memory before selecting additional infrastructure.
