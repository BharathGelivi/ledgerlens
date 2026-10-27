# LedgerLens

Payment-data investigations with source history, tested SQL, and evidence-grounded AI.

The owner is registered solo for the PayPal AI Hackathon. No final entry is submitted. PayPal sandbox authentication/reporting and NVIDIA inference are verified. The sandbox currently returns zero transactions; the populated demonstration is explicitly synthetic.

## Start the application

From PowerShell in this repository folder, first create an environment and install the pinned dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe generate_demo.py
.\.venv\Scripts\python.exe pipeline.py --input fixtures\demo.json --dataset demo
.\.venv\Scripts\python.exe serve.py --dataset demo
```

Open http://127.0.0.1:8011/. Stop with Ctrl+C. The four sections are Overview, Transactions, Pipeline & quality, and How it works. The last section includes an end-to-end lesson and replay exercise.

For a standalone clone, use Python 3.10+, create a virtual environment, install requirements.txt, then run generate_demo.py, pipeline.py --input fixtures/demo.json --dataset demo, and serve.py --dataset demo. A fresh Windows clone/environment and clean Linux CI installation have both passed the tests and demo build.

## Understand the full data journey

1. **Extract: Python, OAuth, PayPal API, JSON.** collect_sandbox.py reads sandbox Transaction Search pages. It saves a snapshot after all pages succeed. It correctly handles a zero-record response, including PayPal omitting transaction_details. The endpoint is fixed to PayPal's sandbox; there are no payment-write operations.
2. **Preserve: DuckDB bronze history.** raw_records retains each distinct JSON payload under its SHA-256 fingerprint. record_sightings tracks repeated observations by run. Observation count is different from transaction count.
3. **Validate: a Python data contract.** Required fields, event-code shape, statuses, timezone-aware timestamps, and decimal amounts are checked. Timestamps become UTC; currencies stay separate. Unusable rows remain in raw storage with a reason in quarantine. Good versions enter valid_records. DECIMAL(20,8) preserves amounts exactly.
4. **Optimize ingestion: set-based SQL.** Validation stays in Python, while database inserts use JSON batches inside a transaction instead of issuing database calls per row. benchmark.py compares the original method and asserts identical normalized records and quarantine outputs.
5. **Resolve state: dbt and window functions.** The dependency chain is conflicts -> payments -> daily_activity. Conflicting latest normalized values at the same key/timestamp are withheld. payments chooses the latest unambiguous state; daily_activity groups those states by initiation date in UTC and currency.
6. **Test, then publish.** Each attempt builds a separate warehouse version, runs dbt models and three SQL checks, and exports Parquet. Only a passing build replaces the active.json pointer. A failed run leaves the last published database intact, so the app can keep reading it during a refresh. Run manifests record source hashes, counts, duration, and result.
7. **Serve: FastAPI and a responsive browser workspace.** Bounded, parameterized endpoints expose currency activity, filtered transactions, version traces, quality findings, and run history. The UI has labelled controls and keyboard-operable actions. Local-host and cross-origin checks protect write endpoints. Credentials and raw payer information are not served.
8. **Explain: NVIDIA NIM.** The verified remote model is nvidia/nemotron-3.5-lightning-30b-a3b. It receives aggregate evidence, quality reasons, and a question. It does not receive transaction IDs, raw payloads, payer details, credentials, or arbitrary database access. SQL calculates; the model explains. The evidence remains visible for checking, and truncated responses are rejected.

Current state assigned to initiation date is not a historical status snapshot, settlement-day report, account balance, revenue calculation, fraud model, or complete fee/FX reconciliation.

## Reproduce the demonstration

The deterministic 30-day input has 1,444 observations: 1,264 unique payloads, 1,256 valid versions, eight quarantined payloads, and one conflicting latest key. Withholding that ambiguous key leaves 1,199 current records.

Search for DEMO-029000000038 in Transactions. Its trace shows pending -> completed with both versions preserved. In Pipeline & quality, inspect DEMO-000000000000 to see the contradictory latest values excluded from totals. Replay the latest input: new unique payloads should be zero; current counts and amounts should remain unchanged, while observation counts increase.

## Configure NVIDIA privately

```powershell
.\.venv\Scripts\python.exe configure_ai.py
```

Paste the key into the masked prompt. It is encrypted for your Windows user in the ignored data folder. Setup makes no API call. Refresh the app after configuration. NVIDIA_API_KEY and optional NVIDIA_MODEL environment variables also work. The existing OpenAI path is available through OPENAI_API_KEY and OPENAI_MODEL.

Each requested investigation makes one cloud call with a 1,200-output-token ceiling. The evidence summarizes all published current records by currency, with global status/quality counts and observed rejection reasons. The AI cannot execute SQL, edit data, or move money. Review its explanation against the displayed evidence. Provider quotas and model availability apply.

## Use actual PayPal sandbox data

The owner's approved Transaction Search permission and encrypted local credentials are configured. No plaintext credential file remains. To collect, build, and view an isolated sandbox dataset:

```powershell
.\.venv\Scripts\python.exe collect_sandbox.py --start 2026-10-26T00:00:00Z --end 2026-10-27T09:00:00Z
.\.venv\Scripts\python.exe pipeline.py --input data\sandbox.json --dataset sandbox
.\.venv\Scripts\python.exe serve.py --dataset sandbox --port 8012
```

Choose dates containing your test activity. PayPal documents reporting delays of up to three hours and a maximum 31-day window. A successful zero-row extract is not a populated payment demonstration. The collector accepts at most 10,000 records/10 MB; use shorter windows above those bounds. Another contributor must configure their own environment variables; Windows-encrypted keys intentionally cannot be used from another account or machine.

Official source: https://developer.paypal.com/api/transaction-search/v1/search-get

## Learn by predicting and checking

- Replay a source snapshot. Predict new payloads before reading the result.
- Trace a status change. Explain why historical versions and current transactions have different counts.
- Inspect an ambiguous key. Explain why arbitrary tie-breaking would produce unreliable figures.
- Change the chart currency. Explain what an explicit FX policy would need before combining currencies.
- Read a quarantine reason and find the corresponding fingerprint in source history.
- Read models/payments.sql and a run's dbt/manifest.json and dbt/run_results.json to connect model dependencies to checks.
- Ask the investigator a question. Check every figure against evidence and separate observed facts from follow-up suggestions.

## Verify

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s . -p test_*.py -v
.\.venv\Scripts\python.exe verify_workspace.py
.\.venv\Scripts\python.exe benchmark.py
```

The HTTP checker expects the deterministic demo on port 8011. It verifies filters, injection resistance, lineage, conflict exclusion, origin checks, reads during refresh, and atomic/idempotent replay. It does not make a paid AI request. See VALIDATION.md.

## Operating limits

One sandbox account per dataset; revisit the transaction/event key before supporting multiple merchants or every reporting category. Currency validation checks shape, not the full provider catalogue. Raw ingestion is incremental/idempotent; dbt tables rebuild. Snapshots are bounded to 50 MB. This is not a streaming lakehouse or production accounting engine.

Run versions/inputs are retained and consume disk. Do not delete the active run. A hard crash can leave pipeline.lock; confirm no writer is running before removing it. The project is inside OneDrive: retained credentials are encrypted, but database-sync locks may still justify an unsynced copy.

DuckDB uses one worker, a 512 MB buffer setting, and a 1 GB spill bound; these do not cap whole-process RAM. No local model weights or GPU training are needed. Add Airflow, Kafka, or ClickHouse when scheduling, real streams, or concurrent workload measurements justify them; more tool names alone do not improve reliability.

No public deployment, production authentication, final Devpost entry, or demo video is included yet. See SUBMISSION.md for the current draft and outstanding delivery steps.


