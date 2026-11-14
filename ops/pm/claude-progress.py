# encoding: UTF-8
# version: 1.0 @20261114: Claude Code 官方 Hooks → Paperclip 每项目一条长期“进展”任务（试跑，单项目）
"""Claude 桌面/CLI 钩子 → Paperclip；只读观察，不启动、不接管、不回写任何会话。"""

import argparse
from datetime import datetime, timezone
import fcntl
import importlib.util
import json
from pathlib import Path
import sys
import time
import uuid

__version__ = 'v1.0'
__platform__ = 'posix'
__pc__ = ['PM']
__py__ = 'py3.11+'

# 复用 Cursor 试点里已验证过的脱敏、原子写入和资源保护，避免两份逻辑分叉。
_spec = importlib.util.spec_from_file_location('cursor_progress', Path(__file__).with_name('cursor-progress.py'))
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

ROOT = base.ROOT
PRIVATE = ROOT / '.paperclip/claude-progress'
LIMIT = base.LIMIT
EVENTS = {
    'UserPromptSubmit': ('in_progress', '你发了新一轮请求'),
    'Stop': ('in_review', '本轮已答完，是否完成待你确认'),
    'StopFailure': ('blocked', '本轮报错，等待处理'),
}
PROMPT_CHARS, REPLY_CHARS = 200, 800


def marker(project):
    return '<!-- claude-progress:' + project['projectId'] + ' -->'


def match_project(config, cwd):
    """按目录前缀归项目；.claude/worktrees/<名> 折回主仓库。不在名单内返回 None。"""
    cwd = str(cwd or '')
    cwd = cwd.split('/.claude/worktrees/')[0].rstrip('/')
    for project in config['projects']:
        root = project['root'].rstrip('/')
        if cwd == root or cwd.startswith(root + '/'):
            return project
    return None


def normalize(payload, project):
    name = payload.get('hook_event_name')
    if name not in EVENTS:
        return None
    session = payload.get('session_id')
    if not isinstance(session, str) or not session or len(session) > 200:
        raise ValueError('缺少有效 session_id')
    status, label = EVENTS[name]
    if name == 'UserPromptSubmit':
        text = base.safe_text(payload.get('prompt'), PROMPT_CHARS)
    elif name == 'Stop':
        text = base.safe_text(payload.get('last_assistant_message'), REPLY_CHARS)
    else:
        text = base.safe_text(payload.get('error') or payload.get('error_message'), 300)
    return {'id': str(uuid.uuid4()), 'projectId': project['projectId'], 'session': session[:8],
            'event': name, 'status': status, 'label': label, 'text': text,
            'at': datetime.now(timezone.utc).isoformat(timespec='seconds')}


def ensure_issue(project, config, api):
    """第一次有动静时建好该项目唯一的进展任务；已有同标记任务则直接复用。"""
    if project.get('issueId'):
        return project['issueId']
    actor = api('GET', '/cli-auth/me')
    if config['companyId'] not in actor.get('companyIds', []):
        raise RuntimeError('组织权限不符')
    tasks = api('GET', '/companies/' + config['companyId'] + '/issues?projectId=' + project['projectId'])
    matches = [t for t in tasks if marker(project) in (t.get('description') or '')]
    if len(matches) > 1:
        raise RuntimeError('同一项目有重复进展任务')
    issue = matches[0] if matches else api('POST', '/companies/' + config['companyId'] + '/issues', {
        'projectId': project['projectId'], 'title': '[Claude] 进展 · ' + project['name'],
        'description': ('自动汇总本机 Claude 桌面中该项目所有对话的最近进展，仅供查看。\n\n'
                        '每条评论只含你发话的开头一小段或 Claude 答复的开头一段；状态只表示最近一次活动，'
                        '不代表项目完成度。请勿把此任务标记为 Done。\n' + marker(project)),
        'status': 'backlog', 'priority': 'low', 'assigneeAgentId': None,
        'assigneeUserId': actor['userId']})
    project['issueId'] = issue['id']
    return issue['id']


def sync(config, state, api):
    deadline = time.monotonic() + 6
    while state['pending'] and time.monotonic() < deadline:
        event = state['pending'][0]
        project = next((p for p in config['projects'] if p['projectId'] == event['projectId']), None)
        if project is None:
            state['pending'].pop(0)
            continue
        issue_id = ensure_issue(project, config, api)
        path = '/issues/' + issue_id
        current = api('GET', path)
        if (current['companyId'] != config['companyId']
                or current.get('projectId') != project['projectId']
                or current.get('assigneeAgentId')
                or marker(project) not in (current.get('description') or '')):
            raise RuntimeError('绑定对象或负责人已变化，停止同步')
        if current['status'] not in {'done', 'cancelled'}:
            receipt = '<!-- claude-event:' + event['id'] + ' -->'
            comments = api('GET', path + '/comments')
            if not any(receipt in (c.get('body') or '') for c in comments):
                body = ('Claude 桌面 · 对话 ' + event['session'] + ' · ' + event['label'] + '\n\n'
                        '事件：`' + event['event'] + '`；采集时间：' + event['at'] + '\n\n'
                        + event['text'] + '\n\n' + receipt)
                api('PATCH', path, {'status': event['status'], 'comment': body,
                    'commentClientRequestId': str(uuid.uuid5(uuid.NAMESPACE_URL, event['id']))})
        state['pending'].pop(0)
    return True


def process(payload, config_path=PRIVATE / 'config.json', api=None):
    config = base.read_json(config_path)
    project = None
    if payload:
        # 不在试跑名单内的目录：在读正文、凭据、状态和建锁之前就退出。
        project = match_project(config, payload.get('cwd'))
        if project is None:
            return {'ignored': True}
    event = normalize(payload, project) if payload else None
    directory = config_path.parent
    base.guard(directory)
    with (directory / 'sync.lock').open('a') as lock:
        end = time.monotonic() + 5
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= end:
                    raise RuntimeError('同步锁等待超时')
                time.sleep(0.05)
        state_path = directory / 'state.json'
        state = base.read_json(state_path) if state_path.exists() else {'pending': []}
        if event:
            if len(state['pending']) >= 32:
                raise RuntimeError('积压超过 32 条，停止并等待处理')
            state['pending'].append(event)
            base.write_json(state_path, state)
        if not state['pending']:
            return {'unchanged': True}
        try:
            result = sync(config, state, api or base.Paperclip())
        finally:
            base.write_json(state_path, state)
            base.write_json(config_path, config)  # 保存首次建好的 issueId
        return {'synced': result, 'pending': len(state['pending'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['hook', 'flush'])
    parser.add_argument('--config', type=Path, default=PRIVATE / 'config.json')
    args = parser.parse_args()
    try:
        if args.mode == 'flush':
            print(json.dumps(process(None, args.config), ensure_ascii=False))
        else:
            data = sys.stdin.buffer.read(LIMIT + 1)
            if len(data) > LIMIT:
                raise RuntimeError('Hook 输入超过 1 MiB')
            process(json.loads(data), args.config)
    except Exception as error:
        # 不打印输入、响应正文或异常细节，避免意外记录凭据；钩子失败不能打扰对话。
        print('Paperclip 进展同步失败（%s）；待同步事件会在下一次事件或 flush 时重试。'
              % type(error).__name__, file=sys.stderr)
        if args.mode != 'hook':
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
