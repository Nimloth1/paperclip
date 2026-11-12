"""试点必须满足的隔离、幂等、失败恢复和状态语义。只用临时目录和伪 API。"""

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('cursor_progress', Path(__file__).with_name('cursor-progress.py'))
bridge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bridge)


class FakeAPI:
    def __init__(self, config):
        self.issue = {'companyId': config['companyId'], 'projectId': config['projectId'],
                      'status': 'backlog', 'assigneeAgentId': None,
                      'description': bridge.marker(config)}
        self.comments = []
        self.calls = []
        self.fail = False
        self.lose_response = False

    def __call__(self, method, path, body=None):
        self.calls.append((method, path, body))
        if self.fail:
            raise ConnectionError('offline')
        if method == 'GET':
            return copy.deepcopy(self.comments if path.endswith('/comments') else self.issue)
        if method == 'PATCH':
            self.issue['status'] = body['status']
            self.comments.append({'body': body['comment']})
            if self.lose_response:
                self.lose_response = False
                raise ConnectionError('response lost after commit')
            return copy.deepcopy(self.issue)
        raise AssertionError('Unexpected mutation')


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.path = self.directory / 'config.json'
        self.config = {'conversationId': 'selected-chat', 'companyId': 'company',
                       'projectId': 'project', 'issueId': 'issue'}
        bridge.write_json(self.path, self.config)
        self.api = FakeAPI(self.config)

    def tearDown(self):
        self.temp.cleanup()

    def payload(self, name, **extra):
        return {'conversation_id': 'selected-chat', 'generation_id': 'turn-1',
                'hook_event_name': name, **extra}

    def run_event(self, payload):
        with patch.object(bridge, 'guard'):
            return bridge.process(payload, self.path, self.api)

    def test_other_conversation_does_not_open_credentials_or_create_state(self):
        with patch.object(bridge, 'Paperclip', side_effect=AssertionError('credential read')):
            result = bridge.process({'conversation_id': 'other'}, self.path)
        self.assertEqual(result, {'ignored': True})
        self.assertEqual([p.name for p in self.directory.iterdir()], ['config.json'])

    def test_realistic_turn_is_in_progress_then_review_and_duplicate_writes_nothing(self):
        start = self.payload('beforeSubmitPrompt', prompt='验证连接')
        self.run_event(start)
        self.assertEqual(self.api.issue['status'], 'in_progress')
        self.run_event(self.payload('afterAgentResponse', text='连接正常'))
        self.run_event(self.payload('stop', status='completed'))
        self.assertEqual(self.api.issue['status'], 'in_review')
        self.assertEqual(len(self.api.comments), 3)
        state = self.directory / 'state.json'
        timestamp = state.stat().st_mtime_ns
        calls = len(self.api.calls)
        self.run_event(self.payload('stop', status='completed'))
        self.assertEqual(state.stat().st_mtime_ns, timestamp)
        self.assertEqual(len(self.api.calls), calls)

    def test_failed_api_leaves_pending_and_next_event_recovers_in_order(self):
        self.api.fail = True
        with self.assertRaises(ConnectionError):
            self.run_event(self.payload('beforeSubmitPrompt', prompt='测试'))
        self.assertEqual(len(bridge.read_json(self.directory / 'state.json')['pending']), 1)
        self.api.fail = False
        self.run_event(self.payload('stop', status='completed'))
        self.assertEqual(len(self.api.comments), 2)
        self.assertEqual(self.api.issue['status'], 'in_review')
        self.assertFalse(bridge.read_json(self.directory / 'state.json')['pending'])

    def test_committed_but_lost_response_does_not_duplicate_comment(self):
        payload = self.payload('stop', status='completed')
        self.api.lose_response = True
        with self.assertRaises(ConnectionError):
            self.run_event(payload)
        self.run_event(payload)
        self.assertEqual(len(self.api.comments), 1)

    def test_closed_task_does_not_reopen_and_reassigned_task_is_rejected(self):
        self.api.issue['status'] = 'done'
        self.run_event(self.payload('beforeSubmitPrompt', prompt='继续'))
        self.assertEqual(self.api.issue['status'], 'done')
        self.assertFalse(self.api.comments)
        self.api.issue['status'] = 'todo'
        self.api.issue['assigneeAgentId'] = 'someone-else'
        with self.assertRaises(RuntimeError):
            self.run_event(self.payload('stop', status='completed'))
        self.assertFalse(self.api.comments)

    def test_late_response_does_not_override_stop(self):
        self.run_event(self.payload('stop', status='completed'))
        self.run_event(self.payload('afterAgentResponse', text='迟到的消息'))
        self.assertEqual(self.api.issue['status'], 'in_review')
        self.assertEqual(len(self.api.comments), 1)

    def test_abort_and_error_do_not_claim_completion(self):
        self.run_event(self.payload('stop', status='aborted'))
        self.assertEqual(self.api.issue['status'], 'todo')
        self.run_event(self.payload('stop', status='error', generation_id='turn-2'))
        self.assertEqual(self.api.issue['status'], 'blocked')
        with self.assertRaises(ValueError):
            bridge.normalize(self.payload('stop', status='unexpected'))

    def test_secret_redaction_and_content_bounds(self):
        value = bridge.safe_text('Bearer privatevalue sk-abcdefghijklmnop API_KEY=privatepassword\n'
                                 '<think>private reasoning</think>\n' + 'x' * 5000)
        for secret in ['privatevalue', 'sk-abcdefghijklmnop', 'privatepassword', 'private reasoning']:
            self.assertNotIn(secret, value)
        self.assertLess(len(value), 1900)

    def test_hook_failure_still_emits_allow_and_does_not_log_prompt(self):
        result = subprocess.run([sys.executable, '-B', str(SPEC.origin), 'hook',
                                 '--config', str(self.directory / 'missing.json')],
                                input=json.dumps(self.payload('beforeSubmitPrompt', prompt='PRIVATE-PROMPT')),
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout), {'continue': True})
        self.assertNotIn('PRIVATE-PROMPT', result.stderr)

    def test_full_outbox_does_not_overwrite_pending_events(self):
        self.api.fail = True
        state_path = self.directory / 'state.json'
        state = {'seen': [], 'pending': [bridge.normalize(self.payload(
            'stop', status='completed', generation_id='pending-' + str(i))) for i in range(32)]}
        bridge.write_json(state_path, state)
        before = state_path.read_bytes()
        with self.assertRaises(RuntimeError):
            self.run_event(self.payload('beforeSubmitPrompt', prompt='new'))
        self.assertEqual(state_path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
