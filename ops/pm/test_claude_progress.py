"""Claude 进展同步的隔离、归项目、幂等和失败恢复。只用临时目录和伪 API。"""

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('claude_progress', Path(__file__).with_name('claude-progress.py'))
bridge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bridge)
base = bridge.base


class FakeAPI:
    def __init__(self):
        self.issues = {}
        self.comments = []
        self.calls = []
        self.fail = False

    def __call__(self, method, path, body=None):
        self.calls.append((method, path))
        if self.fail:
            raise ConnectionError('offline')
        if path == '/cli-auth/me':
            return {'userId': 'u1', 'companyIds': ['co']}
        if method == 'GET' and '/issues?projectId=' in path:
            return copy.deepcopy(list(self.issues.values()))
        if method == 'POST':
            issue = {**body, 'id': 'iss1', 'companyId': 'co'}
            self.issues['iss1'] = issue
            return copy.deepcopy(issue)
        if method == 'GET' and path.endswith('/comments'):
            return copy.deepcopy(self.comments)
        if method == 'GET':
            return copy.deepcopy(self.issues['iss1'])
        if method == 'PATCH':
            self.issues['iss1']['status'] = body['status']
            self.comments.append({'body': body['comment']})
            return copy.deepcopy(self.issues['iss1'])
        raise AssertionError('Unexpected call')


class ClaudeProgressTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'config.json'
        base.write_json(self.path, {'companyId': 'co', 'projects': [
            {'name': 'paperclip', 'projectId': 'p1', 'root': '/work/paperclip'}]})
        self.api = FakeAPI()

    def tearDown(self):
        self.temp.cleanup()

    def hook(self, name, cwd='/work/paperclip', **extra):
        return {'hook_event_name': name, 'session_id': 'abcdef123456', 'cwd': cwd, **extra}

    def test_other_folder_ignored_before_any_io(self):
        result = bridge.process(self.hook('Stop', cwd='/work/other', last_assistant_message='x'),
                                self.path, self.api)
        self.assertEqual(result, {'ignored': True})
        self.assertEqual(self.api.calls, [])
        self.assertFalse((self.path.parent / 'state.json').exists())

    def test_worktree_and_subfolder_fold_into_project(self):
        cfg = base.read_json(self.path)
        for cwd in ['/work/paperclip/server', '/work/paperclip/.claude/worktrees/foo/ui']:
            self.assertEqual(bridge.match_project(cfg, cwd)['projectId'], 'p1')
        self.assertIsNone(bridge.match_project(cfg, '/work/paperclip-old'))

    def test_task_created_once_and_status_follows_latest(self):
        bridge.process(self.hook('UserPromptSubmit', prompt='做登录页'), self.path, self.api)
        self.assertEqual(self.api.issues['iss1']['status'], 'in_progress')
        bridge.process(self.hook('Stop', last_assistant_message='已完成'), self.path, self.api)
        self.assertEqual(self.api.issues['iss1']['status'], 'in_review')
        self.assertEqual(len([c for c in self.api.calls if c[0] == 'POST']), 1)
        self.assertEqual(len(self.api.comments), 2)
        self.assertEqual(base.read_json(self.path)['projects'][0]['issueId'], 'iss1')
        self.assertFalse(self.api.issues['iss1']['assigneeAgentId'])

    def test_text_truncated_and_redacted(self):
        bridge.process(self.hook('UserPromptSubmit', prompt='token=abc123 ' + 'x' * 500),
                       self.path, self.api)
        body = self.api.comments[0]['body']
        self.assertNotIn('abc123', body)
        self.assertNotIn('x' * 250, body)

    def test_failure_kept_in_outbox_then_flushed_without_duplicates(self):
        self.api.fail = True
        with self.assertRaises(ConnectionError):
            bridge.process(self.hook('Stop', last_assistant_message='答复'), self.path, self.api)
        state = base.read_json(self.path.parent / 'state.json')
        self.assertEqual(len(state['pending']), 1)
        self.api.fail = False
        bridge.process(None, self.path, self.api)
        bridge.process(None, self.path, self.api)
        self.assertEqual(len(self.api.comments), 1)
        self.assertEqual(base.read_json(self.path.parent / 'state.json')['pending'], [])

    def test_lost_patch_response_not_duplicated_on_retry(self):
        bridge.process(self.hook('Stop', last_assistant_message='答复'), self.path, self.api)
        event_id = self.api.comments[0]['body'].split('claude-event:')[1].split(' ')[0]
        state = {'pending': [{'id': event_id, 'projectId': 'p1', 'session': 'abcdef12',
                              'event': 'Stop', 'status': 'in_review', 'label': 'l', 'text': 't',
                              'at': 'now'}]}
        base.write_json(self.path.parent / 'state.json', state)
        bridge.process(None, self.path, self.api)
        self.assertEqual(len(self.api.comments), 1)

    def test_done_task_is_not_reopened(self):
        bridge.process(self.hook('Stop', last_assistant_message='a'), self.path, self.api)
        self.api.issues['iss1']['status'] = 'done'
        bridge.process(self.hook('UserPromptSubmit', prompt='b'), self.path, self.api)
        self.assertEqual(self.api.issues['iss1']['status'], 'done')
        self.assertEqual(len(self.api.comments), 1)

    def test_reassigned_task_stops_sync(self):
        bridge.process(self.hook('Stop', last_assistant_message='a'), self.path, self.api)
        self.api.issues['iss1']['assigneeAgentId'] = 'agent'
        with self.assertRaises(RuntimeError):
            bridge.process(self.hook('UserPromptSubmit', prompt='b'), self.path, self.api)
        self.assertEqual(len(self.api.comments), 1)

    def test_cli_hook_never_blocks_and_never_prints_input(self):
        proc = subprocess.run(
            [sys.executable, '-B', str(Path(bridge.__file__ if hasattr(bridge, '__file__') else SPEC.origin)),
             'hook', '--config', str(self.path)],
            input=json.dumps(self.hook('Stop', last_assistant_message='秘密正文')).encode(),
            capture_output=True, timeout=20)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, b'')
        self.assertNotIn('秘密正文'.encode(), proc.stderr)


if __name__ == '__main__':
    unittest.main()
