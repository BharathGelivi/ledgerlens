"""Read PayPal sandbox reporting records. Never connects to live PayPal."""
import argparse
import base64
import json
import os
from datetime import timedelta
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pipeline import DATA, timestamp
from credentials import load

BASE = 'https://api-m.sandbox.paypal.com'


def request_json(request):
    try:
        with urlopen(request, timeout=30) as response:
            content = response.read(10 * 1024 * 1024 + 1)
            if len(content) > 10 * 1024 * 1024:
                raise ValueError('API response exceeds 10 MB')
            return json.loads(content)
    except HTTPError as error:
        # Do not echo response bodies or credentials into logs.
        raise RuntimeError(f'PayPal sandbox returned HTTP {error.code}; check credentials and reporting permissions') from None


def collect(start, end):
    if not timedelta(0) < timestamp(end) - timestamp(start) <= timedelta(days=31):
        raise ValueError('date window must be positive and no longer than 31 days')
    client_id, secret = load()
    auth = base64.b64encode(f'{client_id}:{secret}'.encode()).decode()
    token = request_json(Request(BASE + '/v1/oauth2/token', data=b'grant_type=client_credentials',
                         headers={'Authorization': 'Basic ' + auth,
                                  'Content-Type': 'application/x-www-form-urlencoded'}))['access_token']
    records = []
    page = 1
    while True:
        query = urlencode({'start_date': start, 'end_date': end, 'page_size': 100,
                           'page': page, 'fields': 'transaction_info',
                           'balance_affecting_records_only': 'Y'})
        result = request_json(Request(BASE + '/v1/reporting/transactions?' + query,
                              headers={'Authorization': 'Bearer ' + token}))
        details = result.get('transaction_details')
        if details is None and result.get('total_items') == 0:
            details = []
        if not isinstance(details, list):
            raise ValueError('PayPal reporting response has no valid transaction array')
        records.extend(details)
        if len(records) > 10000:
            raise ValueError('More than 10,000 records; choose a shorter date window')
        if page >= int(result['total_pages']):
            break
        page += 1
    DATA.mkdir(exist_ok=True)
    output = DATA / 'sandbox.json'
    content = json.dumps({'source': 'paypal-sandbox', 'start': start, 'end': end,
                          'transaction_details': records}, indent=2)
    if len(content.encode('utf-8')) > 10 * 1024 * 1024:
        raise ValueError('Snapshot exceeds 10 MB; choose a shorter date window')
    temporary = output.with_suffix('.tmp')
    temporary.write_text(content, encoding='utf-8')
    temporary.replace(output)
    print(f'Saved {len(records)} sandbox records to {output}')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start', required=True, help='UTC timestamp, e.g. 2026-10-26T00:00:00Z')
    parser.add_argument('--end', required=True, help='UTC timestamp, e.g. 2026-10-27T00:00:00Z')
    options = parser.parse_args()
    collect(options.start, options.end)
