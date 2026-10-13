import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
SKILLS_ROOT = SCRIPTS.parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


archive = load('plan_archive')
installer = load('install')


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = self.base / '中文 project'
        self.project.mkdir()
        self.root = self.base / 'archive with spaces'
        self.env = patch.dict(os.environ)
        self.env.start()
        for name in ('PLANNING_ARCHIVE_ROOT', 'LIFETRACKER_ARCHIVE_ROOT', 'PLAN_ID', 'PWF_PLAN_ROOT'):
            os.environ.pop(name, None)
        self.addCleanup(self.env.stop)

    def execute(self, action, **kwargs):
        args = argparse.Namespace(action=action, task=kwargs.get('task'), selector=kwargs.get('selector'))
        if action == 'list':
            return archive.execute(args, self.project, self.root)
        with archive.mutation_lock(self.project, self.root):
            return archive.execute(args, self.project, self.root)

    def contents(self):
        return {name: (self.project / name).read_bytes() if (self.project / name).exists() else None for name in archive.FILES}

    def test_roundtrip_keeps_docs_and_current_backup(self):
        docs = self.project / 'docs'
        docs.mkdir()
        (docs / 'note.md').write_text('keep', encoding='utf-8')
        self.execute('new', task='中文任务 $(literal) `literal`')
        expected = self.contents()
        result = self.execute('new', task='第二任务')
        source = Path(result['backup'])
        (self.project / 'task_plan.md').write_bytes(b'current\r\n')
        result = self.execute('restore', selector=source.name)
        self.assertEqual(self.contents(), expected)
        self.assertEqual((Path(result['backup']) / 'task_plan.md').read_bytes(), b'current\r\n')
        self.assertTrue(source.is_dir())
        self.assertEqual((docs / 'note.md').read_text(), 'keep')

    def test_legacy_second_precision_archive(self):
        source = self.root / 'archive/20260101-120000-legacy'
        source.mkdir(parents=True)
        for name in archive.FILES:
            (source / name).write_bytes(b'legacy\r\n')
        self.execute('restore', selector=source.name)
        self.assertTrue(all(value == b'legacy\r\n' for value in self.contents().values()))

    def test_ambiguous_and_missing_do_not_change_current(self):
        self.execute('new', task='共同任务')
        self.execute('new', task='共同任务')
        self.execute('new', task='共同任务')
        before = self.contents()
        for selector in ('共同任务', 'missing', '../escape', ''):
            with self.assertRaises(ValueError):
                self.execute('restore', selector=selector)
            self.assertEqual(self.contents(), before)

    def test_incomplete_source_does_not_backup_or_replace(self):
        self.execute('new', task='current')
        before = self.contents()
        source = self.root / 'archive/incomplete'
        source.mkdir(parents=True)
        (source / 'task_plan.md').write_text('partial')
        with self.assertRaises(FileNotFoundError):
            self.execute('restore', selector='incomplete')
        self.assertEqual(self.contents(), before)
        self.assertEqual(len(list((self.root / 'archive').iterdir())), 1)

    def test_partial_current_is_backed_up(self):
        (self.project / 'findings.md').write_bytes(b'partial')
        result = self.execute('new', task='next')
        backup = Path(result['backup'])
        self.assertEqual((backup / 'findings.md').read_bytes(), b'partial')
        self.assertFalse((backup / 'task_plan.md').exists())

    def test_replace_failure_rolls_back(self):
        self.execute('new', task='old')
        before = self.contents()
        real_replace = os.replace
        calls = 0

        def fail_second(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('fixture replacement failure')
            return real_replace(*args)

        with patch.object(archive.os, 'replace', side_effect=fail_second):
            with self.assertRaises(OSError):
                self.execute('new', task='next')
        self.assertEqual(self.contents(), before)
        self.assertEqual(len(list((self.root / 'archive').iterdir())), 1)

    def test_archive_root_precedence_and_workspace_guard(self):
        generic, legacy, explicit = (self.base / name for name in ('generic', 'legacy', 'explicit'))
        with patch.dict(os.environ, {'PLANNING_ARCHIVE_ROOT': str(generic), 'LIFETRACKER_ARCHIVE_ROOT': str(legacy)}):
            self.assertEqual(archive.archive_root(self.project), generic.resolve())
            self.assertEqual(archive.archive_root(self.project, str(explicit)), explicit.resolve())
        for root in (self.project, self.project / 'archive', self.base, Path('relative')):
            with self.assertRaises(ValueError):
                archive.archive_root(self.project, str(root))

    def test_git_projects_share_by_origin_and_isolate_others(self):
        for name in ('one', 'two', 'other'):
            folder = self.base / name
            folder.mkdir()
            subprocess.run(['git', 'init', '-q', str(folder)], check=True)
            remote = 'https://example.com/team/' + ('other.git' if name == 'other' else 'shared.git')
            subprocess.run(['git', '-C', str(folder), 'config', 'remote.origin.url', remote], check=True)
        with patch.object(archive.Path, 'home', return_value=self.base / 'home'):
            self.assertEqual(archive.archive_root(self.base / 'one'), archive.archive_root(self.base / 'two'))
            self.assertNotEqual(archive.archive_root(self.base / 'one'), archive.archive_root(self.base / 'other'))

    def test_lifetracker_default_is_compatible(self):
        with patch.object(archive, 'project_identity', return_value=('LifeTracker', 'digest')):
            with patch.object(archive.Path, 'home', return_value=self.base / 'home'):
                expected = self.base / 'home/DevEcoStudioProjects/.claude-plan-archive/LifeTracker'
                self.assertEqual(archive.archive_root(self.project), expected.resolve())

    def test_lock_prevents_write_and_preserves_existing_lock(self):
        self.root.mkdir()
        lock = self.root / '.planning-archive.lock'
        lock.mkdir()
        with self.assertRaises(FileExistsError):
            self.execute('new', task='blocked')
        self.assertTrue(lock.exists())
        self.assertFalse((self.project / '.planning-archive.lock').exists())
        self.assertTrue(all(value is None for value in self.contents().values()))

    def test_named_plan_never_falls_back_to_root(self):
        named = self.project / '.planning/named'
        named.mkdir(parents=True)
        (named / 'task_plan.md').write_text('named')
        with self.assertRaises(ValueError):
            archive.reject_named_plans(self.project)

    def test_installer_backup_and_removes_old_duplicate_logic(self):
        home = self.base / 'home'
        destinations = [home / '.codex/skills', home / '.claude/skills']
        old = destinations[0] / 'new-plan-zh/scripts'
        old.mkdir(parents=True)
        (old / 'plan_archive.py').write_text('old copy')
        installer.install(SKILLS_ROOT, destinations, home / 'backups', dry_run=True)
        self.assertFalse((destinations[1] / 'new-plan-zh').exists())
        installer.install(SKILLS_ROOT, destinations, home / 'backups')
        self.assertFalse((old / 'plan_archive.py').exists())
        self.assertTrue(list((home / 'backups').glob('*/scripts/plan_archive.py')))
        for destination in destinations:
            self.assertTrue((destination / 'planning-archive-zh/scripts/plan_archive.py').exists())
            self.assertTrue((destination / 'restore-plan-zh/SKILL.md').exists())

    def test_installer_failure_restores_old_install(self):
        home = self.base / 'home'
        destination = home / '.codex/skills'
        old = destination / 'planning-archive-zh'
        old.mkdir(parents=True)
        (old / 'marker').write_text('old')
        with patch.object(installer.os, 'replace', side_effect=OSError('fixture install failure')):
            with self.assertRaises(OSError):
                installer.install(SKILLS_ROOT, [destination], home / 'backups')
        self.assertEqual((old / 'marker').read_text(), 'old')


if __name__ == '__main__':
    unittest.main()
