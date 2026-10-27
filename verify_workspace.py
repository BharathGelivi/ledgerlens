"""Assert meaningful behavior against a running local workspace; no external APIs."""
import json
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE = 'http://127.0.0.1:8011'


def get(path, data=None, headers=None):
    with urlopen(Request(BASE + path, data=data, headers=headers or {}), timeout=10) as response:
        return json.load(response)


if __name__ == '__main__':
    initial = get('/workspace')
    assert initial['dataset'] == 'synthetic'
    assert initial['counts'] == {'raw_records': 1264, 'valid_records': 1256,
                                  'quarantine': 8, 'payments': 1199, 'conflicts': 1}
    assert len(initial['tests']) == 3 and all(t['status'] == 'pass' for t in initial['tests'])
    filtered = get('/transactions?status=P&currency=USD')
    assert all(row['status'] == 'P' and row['currency'] == 'USD' for row in filtered['rows'])
    assert get('/transactions?search=x%27%20OR%201%3D1--')['total'] == 0
    trace = get('/trace?transaction_id=DEMO-029000000038&event_code=T0006')
    assert [row['status'] for row in trace['versions']] == ['P', 'S']
    assert trace['current'][0]['status'] == 'S'
    ambiguous = get('/trace?transaction_id=DEMO-000000000000&event_code=T0006')
    assert ambiguous['current'] == [] and len(ambiguous['conflicts']) == 1
    for path, data, headers, expected in [
            ('/transactions?status=X', None, {}, 422),
            ('/replay', b'', {}, 403),
            ('/replay', b'', {'X-LedgerLens': 'workspace', 'Origin': 'https://untrusted.example'}, 403)]:
        try:
            get(path, data, headers)
            raise AssertionError('Expected refusal: ' + path)
        except HTTPError as error:
            assert error.code == expected, error.code
    if not initial['ai_connected']:
        answer = get('/investigate', json.dumps({'question': 'What needs investigation?'}).encode(),
                     {'X-LedgerLens': 'workspace', 'Content-Type': 'application/json'})
        assert answer['mode'] == 'sql-evidence'
        assert answer['evidence']['ambiguous_current_keys'] == 1
    original_run = initial['published_run']['run_id']
    get('/replay', b'', {'X-LedgerLens': 'workspace'})
    during = get('/workspace')
    assert during['counts'] == initial['counts']
    for _ in range(100):
        current = get('/workspace')
        if not current['job']['running']:
            break
        time.sleep(.3)
    assert not current['job']['running'] and current['job']['error'] is None
    assert current['published_run']['run_id'] != original_run
    assert current['published_run']['new_unique_records'] == 0
    assert current['published_run']['replayed_or_duplicate_records'] == 1444
    assert current['counts'] == initial['counts']
    print('PASS: filters, injection resistance, lineage, ambiguity exclusion, three SQL checks, origin protection,')
    print('live reads during refresh, atomic publication, and idempotent replay. No paid AI call made by this check.')
