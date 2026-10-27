"""Compare original per-row insertion with set-based insertion on the same fixture."""
import hashlib
import json
import time
from decimal import InvalidOperation

from generate_demo import generate
from pipeline import DATA, connect, ingest, normalize


def original_ingest(db, records):
    ingest(db, [])
    db.execute('begin')
    for record in records:
        payload = json.dumps(record, sort_keys=True, separators=(',', ':'), allow_nan=False)
        digest = hashlib.sha256(payload.encode()).hexdigest()
        db.execute('insert into raw_records(record_hash,payload) values (?,?) on conflict do nothing',
                   [digest, payload])
        try:
            values = normalize(record)
        except (KeyError, TypeError, ValueError, AttributeError, InvalidOperation) as error:
            db.execute('insert into quarantine values (?,?) on conflict do nothing', [digest, str(error)])
            continue
        db.execute('insert into valid_records values (?,?,?,?,?,?,?,?) on conflict do nothing', [digest, *values])
    db.execute('commit')


if __name__ == '__main__':
    records = generate()['transaction_details']
    measurements, fingerprints = {}, []
    for label, function in [('original_per_row', original_ingest), ('set_based', ingest)]:
        with connect(':memory:') as db:
            started = time.perf_counter()
            function(db, records)
            measurements[label] = round(time.perf_counter() - started, 4)
            fingerprints.append({table: db.execute(f'select * from {table} order by record_hash').fetchall()
                                 for table in ('valid_records', 'quarantine')})
    assert fingerprints[0] == fingerprints[1], 'Optimized output differs from original ingestion'
    result = {'records': len(records), 'environment': 'same process, fresh in-memory DuckDB per method',
              'seconds': measurements, 'speedup': round(measurements['original_per_row'] / measurements['set_based'], 2),
              'scope': 'Single small synthetic ingestion comparison; excludes dbt, disk and cloud collection.'}
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / 'benchmark.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
