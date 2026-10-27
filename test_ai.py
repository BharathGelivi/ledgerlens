import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from briefing import explain, extract_text
from configure_ai import configure, load_ai, DEFAULT_MODEL


class AiTests(unittest.TestCase):
    def test_nvidia_complete_and_truncated_responses(self):
        complete = {'choices': [{'finish_reason': 'stop', 'message': {'content': 'Check the source records.'}}]}
        self.assertEqual(extract_text(complete), 'Check the source records.')
        complete['choices'][0]['finish_reason'] = 'length'
        with self.assertRaises(ValueError):
            extract_text(complete)

    def test_nvidia_request_is_bounded_and_contains_only_supplied_evidence(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            'choices': [{'finish_reason': 'stop', 'message': {'content': 'Eight rows need review.'}}]}).encode()
        with patch('briefing.ai_settings', return_value={'provider': 'nvidia', 'model': DEFAULT_MODEL,
                                                       'api_key': 'fake-test-key'}), \
                patch('briefing.urlopen', return_value=response) as send:
            answer = explain('What needs review?', {'quarantined_unique_records': 8})
            request = send.call_args.args[0]
            body = json.loads(request.data)
            self.assertEqual(request.full_url, 'https://integrate.api.nvidia.com/v1/chat/completions')
            self.assertEqual(body['max_tokens'], 1200)
            self.assertFalse(body['chat_template_kwargs']['enable_thinking'])
            self.assertEqual(json.loads(body['messages'][1]['content'])['evidence'],
                             {'quarantined_unique_records': 8})
            self.assertNotIn('fake-test-key', request.data.decode())
            self.assertEqual(answer, 'Eight rows need review.')

    @unittest.skipUnless(os.name == 'nt', 'Windows user encryption test')
    def test_key_saved_encrypted_and_loaded_without_plaintext_file(self):
        with tempfile.TemporaryDirectory() as folder, patch('configure_ai.AI_FILE', Path(folder) / 'ai.bin'):
            fake = 'nvapi-' + 'testing-only-no-access-' * 3
            configure(fake)
            stored = (Path(folder) / 'ai.bin').read_bytes()
            self.assertNotIn(fake.encode(), stored)
            self.assertEqual(load_ai()['api_key'], fake)
            with self.assertRaises(ValueError):
                configure('invalid')


if __name__ == '__main__':
    unittest.main()
