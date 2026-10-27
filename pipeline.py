"""Versioned payment-data pipeline with tested, atomic publication."""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from collections import Counter
from uuid import uuid4

import duckdb

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('LEDGERLENS_DATA', str(ROOT / 'data'))).resolve()
DB = DATA / 'ledgerlens.duckdb'


def publish_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2), encoding='utf-8')
    temporary.replace(path)


def active_database():
    pointer = DATA / 'active.json'
    if not pointer.exists():
        return DATA / 'ledgerlens.duckdb'
    resolved = (DATA / json.loads(pointer.read_text(encoding='utf-8'))['database']).resolve()
    if DATA.resolve() not in resolved.parents:
        raise ValueError('Published database path is outside project data')
    return resolved


def connect(path=None, read_only=False):
    path = active_database() if path is None else path
    return duckdb.connect(str(path), read_only=read_only, config={
        'threads': 1, 'memory_limit': '512MB',
        'max_temp_directory_size': '1GB',
    })


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError('timestamp must include a timezone')
    return parsed


def normalize(record):
    info = record['transaction_info']
    transaction_id = info['transaction_id']
    event_code = info['transaction_event_code']
    status = info['transaction_status']
    currency = info['transaction_amount']['currency_code']
    if not isinstance(transaction_id, str) or not transaction_id.strip():
        raise ValueError('missing transaction ID')
    if not isinstance(event_code, str) or not re.fullmatch(r'T\d{4}', event_code):
        raise ValueError('invalid event code')
    if status not in ('S', 'P', 'D', 'V'):
        raise ValueError('unknown status')
    if not isinstance(currency, str) or not re.fullmatch(r'[A-Z]{3}', currency):
        raise ValueError('invalid currency shape')
    try:
        amount = Decimal(str(info['transaction_amount']['value']))
    except InvalidOperation:
        raise ValueError('Amount is not a readable number') from None
    if not amount.is_finite() or abs(amount) >= Decimal('1000000000000'):
        raise ValueError('amount outside decimal(20,8) range')
    if amount != amount.quantize(Decimal('0.00000001')):
        raise ValueError('amount has more than eight decimal places')
    initiated = timestamp(info['transaction_initiation_date'])
    updated = timestamp(info['transaction_updated_date'])
    if updated < initiated:
        raise ValueError('update precedes initiation')
    return (transaction_id, event_code, status, currency, amount,
            initiated.astimezone(timezone.utc).replace(tzinfo=None),
            updated.astimezone(timezone.utc).replace(tzinfo=None))


def ingest(db, records, run_id=None):
    db.execute('''create table if not exists raw_records (
        record_hash varchar primary key, payload json not null,
        ingested_at timestamp default current_timestamp)''')
    db.execute('''create table if not exists valid_records (
        record_hash varchar primary key, transaction_id varchar, event_code varchar,
        status varchar, currency varchar, amount decimal(20,8),
        initiated_at timestamp, updated_at timestamp)''')
    db.execute('''create table if not exists quarantine (
        record_hash varchar primary key, reason varchar)''')
    db.execute('''create table if not exists record_sightings (
        run_id varchar, record_hash varchar, occurrences integer,
        primary key (run_id, record_hash))''')
    db.execute('begin')
    try:
        sightings = Counter()
        raw, valid, rejected = [], [], []
        for record in records:
            payload = json.dumps(record, sort_keys=True, separators=(',', ':'), allow_nan=False)
            digest = hashlib.sha256(payload.encode()).hexdigest()
            sightings[digest] += 1
            raw.append((digest, payload))
            try:
                values = normalize(record)
            except (KeyError, TypeError, ValueError, AttributeError, InvalidOperation) as error:
                reason = ('Missing required field: ' + str(error.args[0]).replace('_', ' ')
                          if isinstance(error, KeyError) else str(error))
                rejected.append((digest, reason))
                continue
            valid.append((digest, *values))
        batches = [
            ('raw_records', '(record_hash,payload)', raw, ['varchar', 'json']),
            ('valid_records', '', valid, ['varchar'] * 5 + ['decimal(20,8)', 'timestamp', 'timestamp']),
            ('quarantine', '', rejected, ['varchar', 'varchar']),
            ('record_sightings', '', [(run_id, digest, count) for digest, count in sightings.items()] if run_id else [],
             ['varchar', 'varchar', 'integer']),
        ]
        for table, columns, batch, types in batches:
            if not batch:
                continue
            fields = ','.join(f"json_extract_string(value, '$[{i}]')::{kind}" for i, kind in enumerate(types))
            conflict = 'on conflict(record_hash) do update set reason=excluded.reason' if table == 'quarantine' else 'on conflict do nothing'
            db.execute(f'insert into {table}{columns} select {fields} from json_each(?) {conflict}',
                       [json.dumps(batch, default=str)])
        db.execute('commit')
    except Exception:
        db.execute('rollback')
        raise


def run(source):
    started = time.perf_counter()
    source = Path(source)
    # shortcut: bounded JSON snapshots; stream records when extracts exceed 50 MB.
    if source.stat().st_size > 50 * 1024 * 1024:
        raise ValueError('input exceeds the 50 MB snapshot limit')
    payload = json.loads(source.read_text(encoding='utf-8'))
    records = payload['transaction_details']
    if not isinstance(records, list):
        raise ValueError('transaction_details must be an array')
    DATA.mkdir(parents=True, exist_ok=True)
    lock = DATA / 'pipeline.lock'
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise ValueError('A pipeline run is already active; wait before retrying') from None
    os.close(descriptor)
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid4().hex[:8]
    folder = DATA / 'runs' / run_id
    folder.mkdir(parents=True)
    candidate = folder / 'warehouse.duckdb'
    result = {'run_id': run_id, 'source': source.name, 'input_records': len(records),
              'started_at': datetime.now(timezone.utc).isoformat(), 'status': 'running',
              'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
    try:
        shutil.copy2(source, folder / 'input.json')
        previous = active_database()
        if previous.exists():
            shutil.copy2(previous, candidate)
        with connect(candidate) as db:
            dataset = 'synthetic' if str(payload.get('source', '')).startswith('synthetic') else 'external'
            db.execute('create table if not exists dataset_metadata (dataset varchar)')
            existing = db.execute('select dataset from dataset_metadata').fetchone()
            if existing and existing[0] != dataset:
                raise ValueError('Cannot mix synthetic and external data; use a separate data directory')
            if not existing:
                db.execute('insert into dataset_metadata values (?)', [dataset])
            before = db.execute("select count(*) from information_schema.tables where table_name='raw_records'").fetchone()[0]
            before = db.execute('select count(*) from raw_records').fetchone()[0] if before else 0
            ingest(db, records, run_id)
        environment = dict(os.environ, LEDGERLENS_DB=str(candidate))
        with (folder / 'dbt.log').open('w', encoding='utf-8') as log:
            subprocess.run([sys.executable, '-c', 'from dbt.cli.main import cli; cli()', 'build',
                            '--project-dir', str(ROOT), '--profiles-dir', str(ROOT),
                            '--target-path', str(folder / 'dbt'), '--no-use-colors'],
                           env=environment, check=True, stdout=log, stderr=subprocess.STDOUT, timeout=180)
        with connect(candidate) as db:
            destination = str(folder / 'daily_activity.parquet').replace("'", "''")
            db.execute(f"copy daily_activity to '{destination}' (format parquet, compression zstd)")
            counts = {table: db.execute(f'select count(*) from {table}').fetchone()[0]
                      for table in ('raw_records', 'valid_records', 'quarantine', 'payments', 'conflicts')}
            result.update(counts)
            result.update({'new_unique_records': counts['raw_records'] - before,
                           'replayed_or_duplicate_records': len(records) - (counts['raw_records'] - before),
                           'dataset': dataset, 'status': 'passed'})
        result['elapsed_seconds'] = round(time.perf_counter() - started, 3)
        publish_json(folder / 'run.json', result)
        publish_json(DATA / 'active.json', {'database': candidate.relative_to(DATA).as_posix(), 'run_id': run_id})
    except Exception as error:
        result.update({'status': 'failed', 'error': type(error).__name__})
        raise
    finally:
        result['elapsed_seconds'] = round(time.perf_counter() - started, 3)
        publish_json(folder / 'run.json', result)
        lock.unlink(missing_ok=True)
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'fixtures' / 'synthetic.json')
    parser.add_argument('--dataset', choices=['demo', 'sandbox'], help='Isolated dataset directory')
    options = parser.parse_args()
    if options.dataset:
        DATA = ROOT / 'data' / options.dataset
    run(options.input)
