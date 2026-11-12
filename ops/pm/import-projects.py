# encoding: UTF-8
# version: 1.0 @20261112: 有界扫描 PM 项目，只导入目录元数据并按来源去重；
"""将本机项目目录登记到 Paperclip；默认预览，--apply 才写入。"""

import argparse
import hashlib
import json
import re
import resource
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

__version__ = 'v1.0'
__platform__ = 'posix'
__pc__ = ['PM']
__py__ = 'py3.11+'

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / '.paperclip'
IMPORT = STATE / 'import'
COMPANY = '46d3b9e9-95f2-4fbf-a665-e72f2f825c8d'
API = 'http://127.0.0.1:8822/api'
ROOTS = [Path('/Volumes/ssd/projects'), Path.home() / 'Dropbox/projects']
SKIP = {'node_modules', 'archive', 'archived', 'outputs', 'data', 'input',
        'dist', 'build', 'venv', '__pycache__', 'src', 'docs', 'vendor'}


def guard():
    """元数据小批次的内存、保留空间和私有清单预算。"""
    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss > 128 * 1024 ** 2:
        raise RuntimeError('导入进程峰值内存超过 128 MiB，停止')
    if shutil.disk_usage('/Volumes/ssd').free < 50 * 1024 ** 3:
        raise RuntimeError('SSD 剩余空间不足 50 GiB，停止')
    if sum(p.stat().st_size for p in IMPORT.glob('*.json')) > 50 * 1024 ** 2:
        raise RuntimeError('导入清单超过 50 MiB，停止')


def write_private(path, value):
    text = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    if path.exists() and path.read_text() == text:
        return
    if len(text.encode()) > 2 * 1024 ** 2:
        raise RuntimeError('单份清单超过 2 MiB，停止')
    with path.open('w') as handle:
        path.chmod(0o600)
        handle.write(text)


def valid_directory(path):
    return (path.is_dir() and not path.name.startswith(('.', '_'))
            and path.name not in SKIP
            and '.moved-' not in path.name)


def repo_url(path):
    result = subprocess.run(['git', '-C', str(path), 'config', '--get',
                             'remote.origin.url'], capture_output=True,
                            text=True, timeout=3, check=False)
    # 只保留 GitHub 标准仓库定位；不保存 URL 的用户信息、查询参数或令牌。
    match = re.fullmatch(r'(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)'
                         r'([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?',
                         result.stdout.strip())
    return 'https://github.com/' + match.group(1) if match else None


def collect(catalog):
    candidates = {}
    visited = 0

    def add(path, source):
        if valid_directory(path):
            candidates.setdefault(str(path.resolve()), set()).add(source)

    def walk(path, depth):
        nonlocal visited
        visited += 1
        if visited > 2000:
            raise RuntimeError('扫描目录数超过 2000，停止')
        if not valid_directory(path):
            return
        if (path / '.git').exists():
            add(path, '本机 Git 仓库')
            return
        if depth < 4:
            for child in sorted(path.iterdir()):
                if child.is_dir() and not child.is_symlink():
                    walk(child, depth + 1)

    for root in ROOTS:
        if root.exists():
            for child in sorted(root.iterdir()):
                if child.is_dir():
                    walk(child, 1)
    for item in catalog['projects']:
        path = Path(item['path'])
        if path.resolve() not in [r.resolve() for r in ROOTS]:
            add(path, 'Codex 已登记项目')

    groups = {}
    # SSD 路径优先，迁移前副本及同仓库工作树合并为一个项目。
    def preference(item):
        raw, sources = item
        path = Path(raw)
        return (not raw.startswith('/Volumes/ssd/'), 'Codex 已登记项目' not in sources,
                (path / '.git').is_file(), len(path.parts), raw)

    for raw, sources in sorted(candidates.items(), key=preference):
        guard()
        path = Path(raw)
        remote = repo_url(path) if (path / '.git').exists() else None
        identity = remote.lower() if remote else raw
        key = hashlib.sha256(identity.encode()).hexdigest()[:24]
        entry = groups.setdefault(key, {'key': key, 'name': path.name, 'paths': [],
                                        'repoUrl': remote, 'sources': []})
        entry['paths'].append(raw)
        entry['sources'] = sorted(set(entry['sources']) | sources)

    entries = list(groups.values())
    if len(entries) > 250:
        raise RuntimeError('候选项目超过 250，停止')
    counts = {}
    for entry in entries:
        counts[entry['name']] = counts.get(entry['name'], 0) + 1
    for entry in entries:
        if counts[entry['name']] > 1:
            entry['name'] = Path(entry['paths'][0]).parent.name + '/' + entry['name']
        lines = ['本机项目目录导入；实际进度待核对。', '',
                 '来源：' + '、'.join(entry['sources']),
                 *['PM 路径：`' + p + '`' for p in entry['paths']]]
        if entry['repoUrl']:
            lines.append('仓库：' + entry['repoUrl'])
        lines += ['', '仅登记项目元数据；未读取代码正文、导入聊天或配置执行环境。',
                  '<!-- pm-project-import:' + entry['key'] + ' -->']
        entry['description'] = '\n'.join(lines)
    return sorted(entries, key=lambda x: x['name'].lower())


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--demo-task', action='store_true')
    args = parser.parse_args()
    IMPORT.mkdir(mode=0o700, parents=True, exist_ok=True)
    guard()
    catalog = json.loads((IMPORT / 'codex-projects.json').read_text())
    entries = collect(catalog)
    write_private(IMPORT / 'plan.json', entries)
    print(json.dumps({'mode': 'apply' if args.apply else 'preview',
                      'projects': len(entries), 'merged_paths': sum(len(e['paths']) - 1 for e in entries),
                      'names': [e['name'] for e in entries]}, ensure_ascii=False))
    if not args.apply:
        return

    credentials = json.loads((STATE / 'auth.json').read_text())['credentials']['http://127.0.0.1:8822']
    opener = urllib.request.build_opener(NoRedirect())

    def api(path, body=None):
        guard()
        request = urllib.request.Request(API + path, headers={
            'Authorization': 'Bearer ' + credentials['token'],
            'Content-Type': 'application/json'},
            data=json.dumps(body).encode() if body is not None else None)
        with opener.open(request, timeout=20) as response:
            return json.loads(response.read(4 * 1024 ** 2))

    actor = api('/cli-auth/me')
    if not actor.get('isInstanceAdmin') or COMPANY not in actor.get('companyIds', []):
        raise RuntimeError('管理员或组织授权不匹配')
    projects = api('/companies/' + COMPANY + '/projects')
    result = {'created': 0, 'skipped': 0, 'projects': []}
    for entry in entries:
        marker = '<!-- pm-project-import:' + entry['key'] + ' -->'
        matches = [p for p in projects if marker in (p.get('description') or '')]
        if not matches and any(p['name'] == entry['name'] for p in projects):
            raise RuntimeError('同名项目没有来源标记，停止以免错误合并')
        if len(matches) > 1:
            raise RuntimeError('发现多个同来源项目，停止以免错误合并')
        if matches:
            project = matches[0]
            result['skipped'] += 1
        else:
            project = api('/companies/' + COMPANY + '/projects', {
                'name': entry['name'], 'description': entry['description'],
                'status': 'backlog', 'idempotencyKey': 'pm-project-import-' + entry['key']})
            projects.append(project)
            result['created'] += 1
        result['projects'].append({'sourceKey': entry['key'], 'name': project['name'], 'id': project['id']})
        if not matches:
            write_private(IMPORT / 'result.json', {'projects': result['projects']})

    if args.demo_task:
        project = next(p for p in result['projects'] if p['name'] == 'paperclip')
        title = '手机验收：查看项目目录并创建一条待办'
        tasks = api('/companies/' + COMPANY + '/issues?projectId=' + project['id'])
        existing = next((t for t in tasks if t['title'] == title), None)
        task = existing or api('/companies/' + COMPANY + '/issues', {
            'projectId': project['id'], 'title': title, 'status': 'backlog',
            'priority': 'low', 'assigneeUserId': actor['userId'], 'assigneeAgentId': None,
            'description': '这是手动验收待办，不分配给执行 Agent。\n\n'
            '1. 手机连接同一 Tailscale 网络并登录 Paperclip。\n'
            '2. 打开 Projects，确认能看到导入的项目。\n'
            '3. 点击 New Task，选择项目，填写要求和验收标准，先保存为待办。\n'
            '4. 验收完成后将本任务标为 Done。\n\n'
            '创建记录不会启动 Cursor Desktop；自动执行需要另外配置执行 Agent。'})
        result['demoTask'] = {'id': task['id'], 'identifier': task['identifier'],
                              'created': existing is None, 'status': task['status']}
    persisted = {'projects': result['projects']}
    if result.get('demoTask'):
        persisted['demoTask'] = {k: v for k, v in result['demoTask'].items() if k != 'created'}
    write_private(IMPORT / 'result.json', persisted)
    print(json.dumps({'created': result['created'], 'skipped': result['skipped'],
                      'demoTask': result.get('demoTask'),
                      'peak_rss_mib': round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 ** 2, 1)}, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except urllib.error.HTTPError as error:
        print('Paperclip API HTTP %s；停止，不自动重试写入。' % error.code, file=sys.stderr)
        sys.exit(1)
