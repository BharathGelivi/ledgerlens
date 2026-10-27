import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline import ROOT, connect, ingest, normalize, run
from collect_sandbox import collect
from briefing import extract_text


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads((ROOT / 'fixtures/synthetic.json').read_text())['transaction_details'][0]

    def test_replay_and_quarantine(self):
        with tempfile.TemporaryDirectory() as folder:
            with connect(Path(folder) / 'test.duckdb') as db:
                bad = {'transaction_info': {'transaction_id': 'broken'}}
                for _ in range(2):
                    ingest(db, [self.record, self.record, bad])
                self.assertEqual(db.execute('select count(*) from raw_records').fetchone()[0], 2)
                self.assertEqual(db.execute('select count(*) from valid_records').fetchone()[0], 1)
                self.assertEqual(db.execute('select count(*) from quarantine').fetchone()[0], 1)

    def test_refuses_mixing_synthetic_with_external(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / 'ledgerlens.duckdb'
            with connect(database) as db:
                db.execute("create table dataset_metadata as select 'synthetic' as dataset")
            source = Path(folder) / 'external.json'
            source.write_text(json.dumps({'source': 'paypal-sandbox', 'transaction_details': []}))
            with patch('pipeline.DATA', Path(folder)), \
                    patch('pipeline.subprocess.run') as build:
                with self.assertRaisesRegex(ValueError, 'Cannot mix'):
                    run(source)
                build.assert_not_called()

    def test_rejects_unusable_money_and_time(self):
        for value in ('NaN', 'Infinity', '0.123456789', '1000000000000'):
            row = copy.deepcopy(self.record)
            row['transaction_info']['transaction_amount']['value'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize(row)
        row = copy.deepcopy(self.record)
        row['transaction_info']['transaction_updated_date'] = '2026-10-27T00:00:00'
        with self.assertRaises(ValueError):
            normalize(row)

    def test_exact_decimal(self):
        row = copy.deepcopy(self.record)
        row['transaction_info']['transaction_amount']['value'] = '0.10'
        self.assertEqual(str(normalize(row)[4]), '0.10')

    def test_timezone_normalizes_to_utc(self):
        row = copy.deepcopy(self.record)
        row['transaction_info']['transaction_initiation_date'] = '2026-10-26T00:30:00+05:30'
        self.assertEqual(normalize(row)[5].isoformat(), '2026-10-25T19:00:00')

    def test_ai_response_requires_completed_text(self):
        response = {'status': 'completed', 'output': [{'type': 'message', 'content': [
            {'type': 'output_text', 'text': 'Check quarantined records.'}]}]}
        self.assertEqual(extract_text(response), 'Check quarantined records.')
        with self.assertRaises(ValueError):
            extract_text({'status': 'incomplete', 'output': []})

    def test_missing_credentials_make_no_ai_request(self):
        with patch.dict('os.environ', {}, clear=True), patch('briefing.load_ai', return_value=None), patch('briefing.urlopen') as request:
            from briefing import explain
            with self.assertRaises(ValueError):
                explain('Explain this report', {})
            request.assert_not_called()

    def test_failed_build_keeps_published_database(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / 'ledgerlens.duckdb'
            with connect(database) as db:
                db.execute("create table dataset_metadata as select 'synthetic' as dataset")
                ingest(db, [self.record])
            with patch('pipeline.DATA', Path(folder)), \
                    patch('pipeline.subprocess.run', side_effect=RuntimeError('build failed')):
                with self.assertRaises(RuntimeError):
                    run(ROOT / 'fixtures' / 'synthetic.json')
            self.assertFalse((Path(folder) / 'active.json').exists())
            self.assertFalse((Path(folder) / 'pipeline.lock').exists())
            with connect(database) as db:
                self.assertEqual(db.execute('select count(*) from raw_records').fetchone()[0], 1)
            manifest = next((Path(folder) / 'runs').glob('*/run.json'))
            self.assertEqual(json.loads(manifest.read_text())['status'], 'failed')

    def test_run_lock_prevents_concurrent_builds(self):
        with tempfile.TemporaryDirectory() as folder, patch('pipeline.DATA', Path(folder)):
            (Path(folder) / 'pipeline.lock').write_text('another run')
            with self.assertRaisesRegex(ValueError, 'already active'):
                run(ROOT / 'fixtures' / 'synthetic.json')

    def test_generated_workload_is_repeatable(self):
        from generate_demo import generate
        self.assertEqual(generate(), generate())
        self.assertGreater(len(generate()['transaction_details']), 1200)

    def test_collector_refuses_bad_window_without_network(self):
        with patch('collect_sandbox.request_json') as request:
            with self.assertRaises(ValueError):
                collect('2026-09-01T00:00:00Z', '2026-10-27T00:00:00Z')
            request.assert_not_called()

    def test_collector_paginates_and_preserves_snapshot_on_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'sandbox.json'
            output.write_text('previous successful snapshot')
            with patch('collect_sandbox.DATA', Path(folder)), patch.dict('os.environ', {
                    'PAYPAL_SANDBOX_CLIENT_ID': 'test', 'PAYPAL_SANDBOX_CLIENT_SECRET': 'test'}), \
                    patch('collect_sandbox.request_json', side_effect=[
                        {'access_token': 'fake'},
                        {'transaction_details': [self.record], 'total_pages': 2},
                        RuntimeError('network unavailable')]) as request:
                with self.assertRaises(RuntimeError):
                    collect('2026-10-26T00:00:00Z', '2026-10-27T00:00:00Z')
                self.assertEqual(request.call_count, 3)
                self.assertEqual(output.read_text(), 'previous successful snapshot')

    def test_real_empty_response_shape_is_a_successful_extract(self):
        with tempfile.TemporaryDirectory() as folder, patch('collect_sandbox.DATA', Path(folder)), \
                patch('collect_sandbox.load', return_value=('fake', 'fake')), \
                patch('collect_sandbox.request_json', side_effect=[{'access_token': 'fake'},
                    {'total_items': 0, 'total_pages': 0}]):
            output = collect('2026-10-26T00:00:00Z', '2026-10-27T00:00:00Z')
            self.assertEqual(json.loads(output.read_text())['transaction_details'], [])


if __name__ == '__main__':
    unittest.main()
