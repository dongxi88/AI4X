"""Project task triplet archive. Python 3.10+, standard library only."""
import argparse
from contextlib import contextmanager
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import urlsplit

FILES = ('task_plan.md', 'findings.md', 'progress.md')


def is_link(path):
    if path.is_symlink():
        return True
    if not path.exists():
        return False
    # Python 3.10 exposes reparse tags before Path.is_junction was introduced.
    return getattr(path.lstat(), 'st_reparse_tag', 0) in (0xA000000C, 0xA0000003)


def validate_file(path):
    if is_link(path):
        raise ValueError(f'拒绝通过链接操作文件：{path}')
    if path.exists() and not path.is_file():
        raise ValueError(f'目标不是普通文件：{path}')


def slug(text):
    return re.sub(r'[^0-9A-Za-z._\-\u4e00-\u9fff]+', '-', text).strip('-._')[:60] or 'untitled'


def project_identity(project):
    try:
        remote = subprocess.run(['git', '-C', str(project), 'config', '--get', 'remote.origin.url'],
                                capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        remote = ''
    if remote:
        if '://' not in remote and re.match(r'[^/]+@[^:]+:', remote):
            remote = 'ssh://' + remote.replace(':', '/', 1)
        parsed = urlsplit(remote)
        identity = ((parsed.hostname or '') + parsed.path).removesuffix('.git').rstrip('/')
        name = identity.rsplit('/', 1)[-1]
    else:
        identity, name = str(project), project.name
    return name, hashlib.sha256(identity.encode('utf-8')).hexdigest()[:12]


def archive_root(project, override=None, project_key=None):
    project = project.resolve(strict=True)
    configured = override or os.environ.get('PLANNING_ARCHIVE_ROOT') or os.environ.get('LIFETRACKER_ARCHIVE_ROOT')
    if configured:
        root = Path(configured).expanduser()
    else:
        name, digest = project_identity(project)
        if not project_key and name.lower() == 'lifetracker':
            root = Path.home() / 'DevEcoStudioProjects/.claude-plan-archive/LifeTracker'
        else:
            key = slug(project_key) if project_key else f'{slug(name)}-{digest}'
            root = Path.home() / '.planning-archives' / key
    if not root.is_absolute():
        raise ValueError('归档根目录必须使用绝对路径')
    root = root.resolve()
    if root == project or project in root.parents or root in project.parents:
        raise ValueError('归档根目录必须位于项目外，且不能是项目的父目录')
    return root


@contextmanager
def mutation_lock(project, root):
    acquired = []
    try:
        root.mkdir(parents=True, exist_ok=True)
        for parent in (project, root):
            lock = parent / '.planning-archive.lock'
            lock.mkdir(exist_ok=False)
            acquired.append(lock)
        yield
    finally:
        for lock in reversed(acquired):
            lock.rmdir()


def reject_named_plans(project):
    if os.environ.get('PLAN_ID') or os.environ.get('PWF_PLAN_ROOT') or any((project / '.planning').glob('*/task_plan.md')):
        raise ValueError('此工具仅支持根目录三件套；请先确认命名计划的选定目录，不得回退操作根计划')


def archive_current(project, root, label):
    existing = [name for name in FILES if (project / name).exists()]
    if not existing:
        return None
    directory = root / 'archive' / (datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '-' + slug(label))
    directory.mkdir(parents=True, exist_ok=False)
    for name in existing:
        shutil.copy2(project / name, directory / name)
    index = root / 'INDEX.md'
    validate_file(index)
    with index.open('a', encoding='utf-8', newline='\n') as stream:
        if stream.tell() == 0:
            stream.write('# LifeTracker Planning Archives\n\n')
        stream.write(f'- `{directory.name}` — 来源项目 `{project.name}`\n')
    return directory


def replace_triplet(project, content, backup):
    # Prepare every file before replacement; restore originals if replacement fails.
    with tempfile.TemporaryDirectory(prefix='.plan-stage-', dir=project) as staging:
        stage = Path(staging)
        for name, data in content.items():
            (stage / name).write_bytes(data)
        replaced = []
        try:
            for name in FILES:
                os.replace(stage / name, project / name)
                replaced.append(name)
        except Exception:
            for name in reversed(replaced):
                if backup and (backup / name).exists():
                    shutil.copy2(backup / name, project / name)
                else:
                    (project / name).unlink(missing_ok=True)
            raise


def new_content(task):
    date = datetime.now().strftime('%Y-%m-%d')
    phases = ('需求与现状确认', '方案设计', '执行实现', '测试与验证', '交付总结')
    plan = f'# 任务计划：{task}\n\n## Goal\n围绕“{task}”完成需求、实现、验证与交付。\n\n## Next Step\n确认需求与项目现状。\n\n## Current Phase\n阶段 1：需求与现状确认\n\n## Phases\n'
    for i, phase in enumerate(phases, 1):
        status = 'in_progress' if i == 1 else 'pending'
        plan += f'\n### Phase {i}: {phase}\n- [ ] 完成{phase}\n- **Status:** {status}\n'
    plan += '\n## Decisions\n| 决策 | 理由 |\n|---|---|\n\n## Errors\n| 错误 | 解决方式 |\n|---|---|\n'
    findings = f'# 发现与决策：{task}\n\n## 需求\n- 任务主题：{task}\n\n## 研究发现\n\n## 技术决策\n| 决策 | 理由 |\n|---|---|\n\n## 资源\n'
    progress = f'# 进度日志：{task}\n\n## 会话：{date}\n\n## 当前状态\n- 阶段：1\n- 开始时间：{date}\n\n## 已执行操作\n- 通过 new-plan-zh 创建任务记录。\n\n## 测试结果\n| 测试 | 预期 | 实际 | 状态 |\n|---|---|---|---|\n\n## 错误\n'
    return dict(zip(FILES, (text.encode('utf-8') for text in (plan, findings, progress))))


def execute(args, project, root):
    for name in FILES:
        validate_file(project / name)
    archives = root / 'archive'
    if is_link(archives):
        raise ValueError('归档子目录不能是链接')
    if args.action == 'new':
        task = (args.task or '').strip()
        if not task or '\n' in task or '\r' in task:
            raise ValueError('请提供单行任务名称')
        content = new_content(task)
        backup = archive_current(project, root, task)
        replace_triplet(project, content, backup)
        return {'action': 'new', 'project': str(project), 'archive_root': str(root), 'backup': str(backup) if backup else None}
    candidates = sorted((p for p in archives.iterdir() if p.is_dir() and not is_link(p)), reverse=True) if archives.exists() else []
    if args.action == 'list':
        return {'archive_root': str(root), 'archives': [p.name for p in candidates[:20]]}
    selector = (args.selector or '').strip()
    if not selector or '/' in selector or '\\' in selector:
        raise ValueError('请提供归档目录名或关键词，不要使用路径')
    exact = [p for p in candidates if p.name == selector]
    matches = exact or [p for p in candidates if selector in p.name]
    if len(matches) != 1:
        print(json.dumps({'matches': [p.name for p in matches], 'recent': [p.name for p in candidates[:20]]}, ensure_ascii=False))
        raise ValueError('匹配为空或不唯一，请选择具体归档目录名')
    source = matches[0]
    content = {}
    for name in FILES:
        validate_file(source / name)
        content[name] = (source / name).read_bytes()
    backup = archive_current(project, root, 'before-restore-' + source.name)
    replace_triplet(project, content, backup)
    return {'action': 'restore', 'source': str(source), 'backup': str(backup) if backup else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('new', 'restore', 'list'))
    parser.add_argument('--project', required=True)
    parser.add_argument('--archive-root')
    parser.add_argument('--project-key')
    parser.add_argument('--task')
    parser.add_argument('--selector')
    args = parser.parse_args()
    project = Path(args.project).expanduser().resolve(strict=True)
    if not project.is_dir():
        raise ValueError('项目路径必须是目录')
    root = archive_root(project, args.archive_root, args.project_key)
    if args.action == 'list':
        result = execute(args, project, root)
    else:
        reject_named_plans(project)
        with mutation_lock(project, root):
            result = execute(args, project, root)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
