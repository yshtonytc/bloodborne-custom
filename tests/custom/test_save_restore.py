from pathlib import Path
import sys
import json
import hashlib
import tempfile
import unittest
from unittest import mock

LOCAL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(LOCAL / 'scripts'))
import bbport_save_restore as saves

class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.port = Path(self.temp.name) / 'windows-v1.7/bbport-windows'
        self.port.mkdir(parents=True)
        self.user = self.port / 'user'
        self.current = self.user / 'savedata/1/CUSA01363/SPRJ0005/userdata0000'
        self.current.parent.mkdir(parents=True)
        self.current.write_bytes(b'current progress')
        self.snapshot = self.user / 'exit-save-backups/20261019-120000'
        self.source = self.snapshot / 'savedata'
        (self.source / '1/CUSA01363/SPRJ0005').mkdir(parents=True)
        (self.source / '1/CUSA01363/SPRJ0005/userdata0000').write_bytes(b'chosen progress')

    def restore(self, **kwargs):
        return saves.restore(self.user, self.port, self.source / '1/CUSA01363/SPRJ0005', check_closed=lambda: None, **kwargs)

    def test_selectable_restore_keeps_current_progress_and_old_backup(self):
        result = self.restore()
        self.assertEqual(self.current.read_bytes(), b'chosen progress')
        safety = Path(result['safety']) / 'savedata/1/CUSA01363/SPRJ0005/userdata0000'
        self.assertEqual(safety.read_bytes(), b'current progress')
        self.assertTrue((self.source / '1/CUSA01363/SPRJ0005/userdata0000').exists())
        entries = saves.discover(self.user, self.port)
        self.assertEqual({e['kind'] for e in entries}, {'exit', 'safety'})

    def test_discovery_includes_manual_copies(self):
        manual = self.port.parent.parent / 'save-copies/PC-20261012-120000/SPRJ0005'
        manual.mkdir(parents=True)
        (manual / 'userdata0000').write_bytes(b'manual')
        entries = saves.discover(self.user, self.port)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]['titles'], ['CUSA01363'])
        self.assertEqual(entries[1]['kind'], 'manual')

    def test_busy_game_is_rejected_without_modifying_saves(self):
        with self.assertRaisesRegex(RuntimeError, 'running'):
            saves.restore(self.user, self.port, self.source / '1/CUSA01363/SPRJ0005',
                check_closed=mock.Mock(side_effect=RuntimeError('Game running')))
        self.assertEqual(self.current.read_bytes(), b'current progress')
        self.assertFalse((self.user / 'save-restore-safety').exists())

    def test_game_started_during_copy_prevents_commit(self):
        check = mock.Mock(side_effect=[None, RuntimeError('Game running')])
        with self.assertRaisesRegex(RuntimeError, 'running'):
            saves.restore(self.user, self.port, self.source / '1/CUSA01363/SPRJ0005', check_closed=check)
        self.assertEqual(self.current.read_bytes(), b'current progress')
        self.assertFalse(list(self.user.glob('.restore-*')))

    def test_failed_publish_rolls_original_directory_back(self):
        original = Path.rename
        def rename(path, target):
            if path.name == 'SPRJ0005' and path.parent.name.startswith('.restore-'):
                raise OSError('simulated publish failure')
            return original(path, target)
        with mock.patch.object(Path, 'rename', rename):
            with self.assertRaisesRegex(OSError, 'publish failure'): self.restore()
        self.assertEqual(self.current.read_bytes(), b'current progress')
        self.assertTrue(saves.discover(self.user, self.port))
        self.assertFalse(list(self.user.glob('.save-before-restore-*')))

    def test_unknown_source_cannot_be_restored(self):
        with self.assertRaises(ValueError):
            saves.restore(self.user, self.port, self.port / 'elsewhere', check_closed=lambda: None)
        self.assertEqual(self.current.read_bytes(), b'current progress')

    def test_two_restores_cannot_run_together(self):
        with saves._restore_lock(self.user):
            with self.assertRaisesRegex(RuntimeError, 'already running'): self.restore()
        self.assertEqual(self.current.read_bytes(), b'current progress')

    def test_corrupt_exit_snapshot_is_rejected_before_safety_copy(self):
        record = {'sha256': {'1/CUSA01363/SPRJ0005/userdata0000': '0' * 64}}
        (self.snapshot / 'backup.json').write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, 'SHA-256'): self.restore()
        self.assertEqual(self.current.read_bytes(), b'current progress')
        self.assertFalse((self.user / 'save-restore-safety').exists())

    def test_other_games_are_preserved(self):
        other = self.user / 'savedata/1/CUSA99999/save'
        other.parent.mkdir(parents=True)
        other.write_bytes(b'other game')
        self.restore()
        self.assertEqual(other.read_bytes(), b'other game')

if __name__ == '__main__': unittest.main()
