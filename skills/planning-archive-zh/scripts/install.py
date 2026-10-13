"""Install the three sibling skills together; source remains in AI4X."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import tempfile

SKILLS = ('planning-archive-zh', 'new-plan-zh', 'restore-plan-zh')


def is_link(path):
    return path.is_symlink() or (path.exists() and getattr(path.lstat(), 'st_reparse_tag', 0) in (0xA000000C, 0xA0000003))


def install(source, destinations, backup_root, dry_run=False):
    source = source.resolve(strict=True)
    for name in SKILLS:
        if not (source / name / 'SKILL.md').is_file():
            raise ValueError(f'来源缺少技能：{name}，请使用完整 AI4X skills 目录')
    report = []
    for destination in destinations:
        destination = destination.expanduser().resolve()
        for name in SKILLS:
            target = destination / name
            if is_link(target):
                raise ValueError(f'拒绝替换链接安装目录：{name}')
            if target == source / name or source in target.parents:
                raise ValueError('安装目录不能覆盖源码')
        report.append({'destination': str(destination), 'skills': list(SKILLS)})
    if dry_run:
        return report
    changes = []
    backup_root = backup_root.expanduser().resolve()
    backup_root.mkdir(parents=True, exist_ok=True)
    try:
        for entry in report:
            destination = Path(entry['destination'])
            destination.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='.planning-install-', dir=destination) as staging:
                for name in SKILLS:
                    shutil.copytree(source / name, Path(staging) / name,
                                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
                for name in SKILLS:
                    target = destination / name
                    backup = None
                    if target.exists():
                        backup = backup_root / (datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '-' + name)
                        shutil.copytree(target, backup)
                    changes.append((target, backup, destination))
                    if backup:
                        # Check the resolved deletion target stays below this installation directory.
                        if target.resolve().parent != destination:
                            raise ValueError('安装目标越界')
                        shutil.rmtree(target)
                    os.replace(Path(staging) / name, target)
    except Exception:
        for target, backup, destination in reversed(changes):
            if target.exists():
                if target.resolve().parent != destination:
                    raise ValueError('回滚目标越界')
                shutil.rmtree(target)
            if backup:
                shutil.copytree(backup, target)
        raise
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--targets', nargs='+', choices=('codex', 'claude'), default=['codex', 'claude'])
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--source-root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    bases = {'codex': args.home / '.codex/skills', 'claude': args.home / '.claude/skills'}
    targets = [bases[name] for name in dict.fromkeys(args.targets)]
    result = install(args.source_root, targets, args.home / '.planning-skill-backups', args.dry_run)
    print(json.dumps({'dry_run': args.dry_run, 'installed': result}, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
