"""Deterministic synthetic workload. No real customer or payment information."""
import copy
import json
import random
from datetime import datetime, timedelta, timezone

from pipeline import ROOT


def generate():
    randomizer = random.Random(42)
    records = []
    first = datetime(2026, 9, 27, 8, tzinfo=timezone.utc)
    for day in range(30):
        for index in range(40):
            created = first + timedelta(days=day, minutes=index * 13)
            status = randomizer.choices(['S', 'P', 'D', 'V'], [80, 10, 6, 4])[0]
            amount = randomizer.randint(100, 25000)
            record = {'transaction_info': {
                'transaction_id': f'DEMO-{day:03d}{index:09d}',
                'transaction_event_code': 'T0006', 'transaction_status': status,
                'transaction_amount': {'currency_code': ['USD', 'INR', 'EUR'][index % 3],
                                       'value': f'{amount // 100}.{amount % 100:02d}'},
                'transaction_initiation_date': created.isoformat(),
                'transaction_updated_date': (created + timedelta(minutes=1)).isoformat()}}
            records.append(record)
            if index % 7 == 0:
                records.append(copy.deepcopy(record))
            if status == 'P' and index % 2 == 0:
                update = copy.deepcopy(record)
                update['transaction_info']['transaction_status'] = 'S'
                update['transaction_info']['transaction_updated_date'] = (created + timedelta(hours=3)).isoformat()
                records.append(update)
    conflicting = copy.deepcopy(records[0])
    conflicting['transaction_info']['transaction_amount']['value'] = '999.99'
    records.append(conflicting)
    for index in range(8):
        bad = copy.deepcopy(records[index + 4])
        bad['transaction_info']['transaction_amount']['value'] = 'unreadable'
        bad['transaction_info']['transaction_id'] = f'DEMO-INVALID-{index}'
        records.append(bad)
    return {'source': 'synthetic-ledgerlens-demonstration',
            'description': 'Deterministic 30-day simulation; duplicates, status updates, invalid amounts, and one conflicting current key.',
            'transaction_details': records}


if __name__ == '__main__':
    output = ROOT / 'fixtures' / 'demo.json'
    payload = generate()
    output.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(f'Created {len(payload["transaction_details"])} synthetic observations at {output}')
