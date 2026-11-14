# encoding: UTF-8
# version: 1.0 @20261112: 单条现有 Cursor Desktop 会话的事件式进度同步试点；
"""Cursor 官方 Hooks → Paperclip 人工任务；不启动或接管 Agent。"""

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import sys
import time
import urllib.request
import uuid

__version__ = 'v1.0'
__platform__ = 'posix'
__pc__ = ['PM']
__py__ = 'py3.11+'

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / '.paperclip/cursor-progress'
API = 'http://127.0.0.1:8822/api'
LIMIT = 1024 * 1024
PHASE = {'bootstrap': 0, 'beforeSubmitPrompt': 1, 'afterAgentResponse': 2, 'stop': 3}


def safe_text(value, limit=1800):
    """仅同步有限的可见文本；常见凭据做脱敏，不处理工具输出和思考。"""
    value = str(value or '')
    value = re.sub(r'(?is)<think>.*?</think>', '[省略思考]', value)
    value = re.sub(r'(?i)Bearer\s+\S+', 'Bearer [已隐藏]', value)
    value = re.sub(r'\b(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]{12,}', '[已隐藏凭据]', value)
    value = re.sub(r'(?i)((?:[\w-]*(?:token|secret|password|api[_-]?key))\s*[=:]\s*)'
                   r'[^\s,;]+', r'\1[已隐藏]', value)
    value = value.replace('<!--', '&lt;!--').replace('-->', '--&gt;').replace('\x00', '')
    return value[:limit] + ('\n[超过同步长度，已截断]' if len(value) > limit else '')


def read_json(path):
    with path.open('rb') as handle:
        data = handle.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise RuntimeError('单文件超过 1 MiB')
    return json.loads(data)


def write_json(path, value):
    """原子替换，内容相同时不触碰文件。"""
    data = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
    if len(data) > LIMIT:
        raise RuntimeError('单文件超过 1 MiB')
    if path.exists() and path.read_bytes() == data:
        return
    temp = path.with_suffix('.tmp')
    with temp.open('wb') as handle:
        os.chmod(temp, 0o600)
        handle.write(data)
    temp.replace(path)


def guard(directory):
    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss > 128 * 1024 ** 2:
        raise RuntimeError('脚本内存超过 128 MiB')
    if shutil.disk_usage('/Volumes/ssd').free < 50 * 1024 ** 3:
        raise RuntimeError('SSD 保留空间不足 50 GiB')
    if sum(p.stat().st_size for p in directory.glob('*') if p.is_file()) > 10 * LIMIT:
        raise RuntimeError('试点私有数据超过 10 MiB')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Paperclip:
    def __init__(self, timeout=2):
        auth = read_json(ROOT / '.paperclip/auth.json')
        self.token = auth['credentials']['http://127.0.0.1:8822']['token']
        self.timeout = timeout
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def __call__(self, method, path, body=None):
        request = urllib.request.Request(API + path, method=method, headers={
            'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json'},
            data=json.dumps(body).encode() if body is not None else None)
        with self.opener.open(request, timeout=self.timeout) as response:
            data = response.read(4 * LIMIT + 1)
        if len(data) > 4 * LIMIT:
            raise RuntimeError('API 响应超过预算')
        return json.loads(data)


def normalize(payload):
    name = payload.get('hook_event_name')
    if name not in PHASE:
        return None
    generation = payload.get('generation_id')
    if not isinstance(generation, str) or not generation or len(generation) > 200:
        raise ValueError('缺少有效 generation_id')
    status, label, text = 'in_progress', '正在处理', ''
    if name == 'beforeSubmitPrompt':
        label, text = '已提交新一轮请求', safe_text(payload.get('prompt'), 600)
    elif name == 'afterAgentResponse':
        label, text = 'Cursor 已生成回复，等待本轮结束事件', safe_text(payload.get('text'))
    else:
        result = payload.get('status')
        if result not in {'completed', 'aborted', 'error'}:
            raise ValueError('未知结束状态')
        status, label = {
            'completed': ('in_review', '本轮已结束，任务完成情况待人工确认'),
            'aborted': ('todo', '本轮已中断，等待继续'),
            'error': ('blocked', '本轮报错，等待处理'),
        }[result]
        if name == 'bootstrap':
            label = '历史会话最近一轮已结束；任务完成情况待人工确认'
            text = safe_text(payload.get('text'))
    identity = json.dumps([generation, name, status, text], ensure_ascii=False)
    return {'id': hashlib.sha256(identity.encode()).hexdigest(), 'generation': generation,
            'phase': PHASE[name], 'event': name, 'status': status, 'label': label,
            'text': text, 'at': datetime.now(timezone.utc).isoformat(timespec='seconds')}


def marker(config):
    return '<!-- cursor-progress:' + config['conversationId'] + ' -->'


def description(config):
    return ('此任务跟踪现有 Cursor Desktop 会话，仍在 Cursor 中工作。\n\n'
            '原始任务：\n' + config['request'] + '\n\n'
            '来源会话：' + config['title'] + '\n'
            '会话 ID：`' + config['conversationId'] + '`\n'
            '本机记录：`' + config['transcriptPath'] + '`\n\n'
            '进度见评论。历史回复只代表当时情况；结束一轮不会自动标记任务 Done。\n'
            '人工验收后可标记 Done；关闭后的任务不会被同步脚本重新打开。\n'
            + marker(config))


def sync(config, state, api):
    """只更新已绑定、仍由人管理的任务；评论使用稳定幂等 ID。"""
    issue_path = '/issues/' + config['issueId']
    current = api('GET', issue_path)
    if (current['companyId'] != config['companyId']
            or current.get('projectId') != config['projectId']
            or current.get('assigneeAgentId')
            or marker(config) not in (current.get('description') or '')):
        raise RuntimeError('绑定对象或负责人已变化，停止同步')
    if current['status'] in {'done', 'cancelled'}:
        return False
    # 已应用的旧事件不覆盖更新的阶段；积压至多在下一次事件/手动 flush 重试。
    deadline = time.monotonic() + 6
    while state['pending'] and time.monotonic() < deadline:
        event = state['pending'][0]
        applied = state.get('last', {})
        if applied.get('generation') == event['generation'] and applied.get('phase', -1) > event['phase']:
            state['seen'] = (state['seen'] + [event['id']])[-100:]
            state['pending'].pop(0)
            continue
        receipt = '<!-- cursor-event:' + event['id'] + ' -->'
        comments = api('GET', issue_path + '/comments')
        if not any(receipt in (c.get('body') or '') for c in comments):
            # GET 后到 PATCH 前不向任何 Agent 分配任务，也不发送唤醒操作。
            body = ('Cursor Desktop · ' + event['label'] + '\n\n'
                    '事件：`' + event['event'] + '`；采集时间：' + event['at'] + '\n\n'
                    + event['text'] + '\n\n' + receipt)
            api('PATCH', issue_path, {'status': event['status'], 'comment': body,
                'commentClientRequestId': str(uuid.uuid5(uuid.NAMESPACE_URL,
                    config['conversationId'] + ':' + event['id']))})
        state['last'] = event
        state['seen'] = (state['seen'] + [event['id']])[-100:]
        state['pending'].pop(0)
    return True


def process(payload, config_path=PRIVATE / 'config.json', api=None):
    config = read_json(config_path)
    # 必须在读取正文、令牌、状态及创建锁文件之前排除其他会话。
    if payload and payload.get('conversation_id') != config['conversationId']:
        return {'ignored': True}
    event = normalize(payload) if payload else None
    directory = config_path.parent
    guard(directory)
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
        state = read_json(state_path) if state_path.exists() else {'seen': [], 'pending': []}
        if event and (event['id'] in state['seen']
                      or any(e['id'] == event['id'] for e in state['pending'])):
            event = None
        if event:
            if len(state['pending']) >= 32:
                raise RuntimeError('积压超过 32 条，停止并等待处理')
            state['pending'].append(event)
            write_json(state_path, state)
        if not state['pending']:
            return {'unchanged': True}
        active_api = api or Paperclip()
        result = sync(config, state, active_api)
        write_json(state_path, state)
        return {'synced': result, 'pending': len(state['pending'])}


def bootstrap(config_path):
    config = read_json(config_path)
    path = Path(config['transcriptPath']).resolve()
    path.relative_to((Path.home() / '.cursor/projects').resolve())
    if path.stem != config['conversationId'] or path.stat().st_size > LIMIT:
        raise RuntimeError('试点记录路径或大小不符')
    messages = []
    last = None
    with path.open() as handle:
        for line in handle:
            entry = json.loads(line)
            if entry.get('role') == 'assistant':
                content = entry.get('message', {}).get('content', [])
                text = '\n'.join(v.get('text', '') for v in content if v.get('type') == 'text')
                if text:
                    messages.append(text)
            if entry.get('type') == 'turn_ended':
                last = entry.get('status')
    if last != 'success':
        raise RuntimeError('历史记录未确认本轮成功结束，不猜测状态')
    # 首次建任务允许服务冷启动；日常 Hook 的短超时不拖住用户提交。
    api = Paperclip(timeout=20)
    if not config.get('issueId'):
        actor = api('GET', '/cli-auth/me')
        if config['companyId'] not in actor.get('companyIds', []):
            raise RuntimeError('组织权限不符')
        tasks = api('GET', '/companies/' + config['companyId'] + '/issues?projectId=' + config['projectId'])
        matches = [t for t in tasks if marker(config) in (t.get('description') or '')]
        if len(matches) > 1:
            raise RuntimeError('同一来源有重复任务')
        issue = matches[0] if matches else api('POST', '/companies/' + config['companyId'] + '/issues', {
            'projectId': config['projectId'], 'title': '[Cursor] ' + config['title'],
            'description': description(config), 'status': 'backlog', 'priority': 'low',
            'assigneeAgentId': None, 'assigneeUserId': actor['userId']})
        config['issueId'] = issue['id']
        config['identifier'] = issue['identifier']
        write_json(config_path, config)
    text = messages[-1] if messages else '历史记录没有可见回复。'
    return process({'conversation_id': config['conversationId'], 'generation_id': 'historical-' + hashlib.sha256(text.encode()).hexdigest(),
                    'hook_event_name': 'bootstrap', 'status': 'completed', 'text': text}, config_path, api)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['hook', 'bootstrap', 'flush'])
    parser.add_argument('--config', type=Path, default=PRIVATE / 'config.json')
    args = parser.parse_args()
    payload = None
    try:
        if args.mode == 'bootstrap':
            print(json.dumps(bootstrap(args.config), ensure_ascii=False))
        elif args.mode == 'flush':
            print(json.dumps(process(None, args.config), ensure_ascii=False))
        else:
            data = sys.stdin.buffer.read(LIMIT + 1)
            if len(data) > LIMIT:
                raise RuntimeError('Hook 输入超过 1 MiB')
            payload = json.loads(data)
            process(payload, args.config)
    except Exception as error:
        # 不打印响应正文、输入、URL 或异常细节，避免意外记录凭据。
        print('Paperclip 进度同步失败（%s）；已保存的待同步事件可在下一次事件或 flush 重试。'
              % type(error).__name__, file=sys.stderr)
        if args.mode != 'hook':
            return 1
    finally:
        if args.mode == 'hook':
            print(json.dumps({'continue': True} if payload and payload.get('hook_event_name') == 'beforeSubmitPrompt' else {}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
