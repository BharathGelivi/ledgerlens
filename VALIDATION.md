# Verification - October 27, 2026

## Passing checks

- Sixteen Python tests cover replay, quarantine, exact decimal amounts, UTC normalization, source separation, failed-build preservation, concurrency locks, repeatable fixtures, collection failure, actual empty-response handling, NVIDIA response/request handling, no secret in prompts, and encrypted-key round-trip.
- Three real dbt checks: unique current keys, ambiguous keys excluded, summary/detail agreement.
- The isolated 30-day fixture has 1,444 observations; 1,264 distinct payloads; 1,256 valid versions; eight quarantined rows; one ambiguous latest key; 1,199 current records.
- Real HTTP checks cover parameterized filters, injection resistance, status-change lineage, ambiguity exclusion, origin protection, reads during refresh, and stable counts with zero new payloads on replay.
- Browser checks cover populated overview, transaction explorer, trace timeline, pipeline checks/history, and source labelling.
- Real PayPal sandbox OAuth and Transaction Search succeeded. Reporting returned zero transactions, and the isolated sandbox pipeline passed with zero rows. No populated sandbox payment demonstration is claimed.
- Real NVIDIA inference succeeded with nvidia/nemotron-3.5-lightning-30b-a3b. The owner's key is encrypted locally. The old initial model was unavailable, so an actually accessible current model was selected. Responses are checked for completion; evidence is visible for human review.
- Devpost solo registration succeeded after explicit agreement approval. The separate project entry was subsequently completed and submitted on October 27, 2026; Devpost displayed Project submitted. Entry: https://devpost.com/software/ledgerlens-o5hndg. Public 2:32 video: https://youtu.be/GL0EV9CTQqo (YouTube checks complete, no issues found).
- The dedicated public source repository is https://github.com/BharathGelivi/ledgerlens. Its clean Linux GitHub Actions installation, tests, and demo build passed. A fresh Windows clone with its own Python environment also passed all sixteen tests and the isolated demo build; uv needed copy mode because OneDrive rejected hardlinks.

## Measured results

The fresh isolated demo build took 7.725 seconds including dbt startup. A later replay took 7.491 seconds.

The same-process microbenchmark used fresh in-memory DuckDB databases and identical 1,444-observation inputs. Original per-row ingestion took 21.2549 seconds; set-based ingestion took 0.0515 seconds. Normalized and quarantine outputs matched exactly. This single microbenchmark excludes dbt, disk, API collection, and larger workloads; it is not a claim that the whole application is hundreds of times faster.

DuckDB uses one worker, a 512 MB buffer setting, and a 1 GB temporary spill bound. Whole-process peak RAM has not been measured. Model inference runs remotely.

## Environment and delivery gaps

Windows restricted execution initially blocked localhost sockets and one temporary file replacement. Actual HTTP verification and the full test suite passed outside those restrictions. No production workaround was added for the testing restriction.

Remaining validation gap: nonzero sandbox activity through reporting. Public source, fresh-clone verification, public narrated walkthrough and final entry submission are complete. Public deployment and production accounting/authentication are outside the current implementation.

Generated datasets, encrypted credentials, local source snapshots, dbt user identifiers, logs, and warehouse files must stay out of the public archive.
