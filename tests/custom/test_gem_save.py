"""Isolated save fixtures: exact write ranges, stale selections, backup, rollback and locks."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock

LOCAL = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(LOCAL/'scripts'), str(LOCAL/'launcher')]
import bbport_gem_save as gems


def fixture():
    data = bytearray(gems.SAVE_SIZE)
    struct.pack_into('<I', data, 12, 84)
    for index, (kind, shape) in enumerate(((1, 1), (1, 4), (2, 1))):
        struct.pack_into('<10I', data, 84+index*40, 0xc0800041+index, (0x80000000 | 90080),
                         kind, shape, *([126208, 37107]+[gems.EMPTY]*4 if kind == 1 else [1100000]+[gems.EMPTY]*5))
    at = 0x400
    for offset, value in zip(gems.characters.OFFSETS, (30, 20, 20, 20, 10, 10)):
        struct.pack_into('<I', data, at+offset, value)
    struct.pack_into('<I', data, at+gems.characters.LEVEL, 60)
    data[at+gems.characters.NAME:at+gems.characters.NAME+8] = '测试猎人'.encode('utf-16-le')
    return bytes(data)


class GemTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.port = Path(self.temp.name)/'port'
        self.user = self.port/'user'
        self.folder = gems.saves.save_dir(self.user)
        self.folder.mkdir(parents=True)
        self.path = self.folder/'userdata0000'
        self.data = fixture()
        self.path.write_bytes(self.data)
        (self.folder/'backup0000').write_bytes(self.data)
        (self.folder/'userdata0001').write_bytes(bytes(gems.SAVE_SIZE))
        (self.folder/'other.bin').write_bytes(b'untouched')
        self.info = gems.load(self.user, 0)
        self.gem = self.info['gems'][0]
        self.new = [126619, 41218] + [gems.EMPTY]*4

    def apply(self, **kwargs):
        return gems.apply(self.user, self.port, 0, self.info['sha256'], self.gem['handle'], self.new,
                          check_closed=kwargs.get('check_closed', lambda: None))

    def test_parser_reads_gems_not_runes_or_empty_characters(self):
        self.assertEqual(len(self.info['gems']), 2)
        self.assertEqual(len(gems.list_characters(self.user)), 1)

    def test_droplet_edit_round_trip_preserves_provenance(self):
        data = bytearray(self.data)
        struct.pack_into('<10I', data,84,0xc0800041,0x80000000|90250,1,63,
                         126515,47217,*([gems.EMPTY]*4))
        original = bytes(data)
        gem = gems.parse(original)['gems'][0]
        changed = gems.rewrite(original,gem['handle'],gem['record'],
                               [126517,41215,*([gems.EMPTY]*4)],'lantern-hamlet')
        self.assertEqual(changed[:100],original[:100])
        self.assertEqual(changed[124:],original[124:])
        reread = gems.parse(changed)['gems'][0]
        self.assertEqual(reread['effects'][:2],[126517,41215])
        self.assertEqual(reread['shape'],63)
        self.assertEqual(reread['source'],gem['source'])

    def test_inventory_storage_and_equipped_locations(self):
        data = bytearray(self.data)
        # The GA equipment records follow the upgrade table; slot references are handles.
        struct.pack_into('<5I', data, 204, 0x808000bf, 5001000, 250, 7, 1)
        for i in range(5):
            struct.pack_into('<II', data, 224+8*i, 1 if i == 0 else 0x80000000,
                             self.gem['handle'] if i == 0 else 0)
        inv = 0x400+gems.characters.NAME+468
        struct.pack_into('<4I', data, inv+34268, 0xfffff040, 0xc0800042, (0x80000000 | 90080), 1)
        parsed = gems.parse(bytes(data))
        self.assertEqual([r['location'] for r in parsed['gems']], ['已镶嵌', '仓库'])

    def test_only_selected_effect_bytes_change_and_backup_is_restorable(self):
        result = self.apply()
        edited = self.path.read_bytes()
        self.assertEqual(edited[:100], self.data[:100])
        self.assertEqual(edited[124:], self.data[124:])
        self.assertEqual(edited, (self.folder/'backup0000').read_bytes())
        self.assertEqual((self.folder/'other.bin').read_bytes(), b'untouched')
        safety = Path(result['safety'])
        self.assertEqual((safety/gems.saves.SAVE_REL/'userdata0000').read_bytes(), self.data)
        self.assertTrue(any(Path(e['path']).resolve() == (safety/gems.saves.SAVE_REL).resolve() for e in gems.saves.discover(self.user, self.port)))
        gems.saves.restore(self.user, self.port, safety/gems.saves.SAVE_REL, check_closed=lambda: None)
        self.assertEqual(self.path.read_bytes(), self.data)

    def test_stale_file_rejected_before_backup(self):
        self.path.write_bytes(self.data[:-1]+b'X')
        with self.assertRaisesRegex(ValueError, '已变化'):
            self.apply()
        self.assertFalse((self.user/'save-restore-safety').exists())

    def test_busy_game_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'running'):
            self.apply(check_closed=mock.Mock(side_effect=RuntimeError('Game running')))
        self.assertEqual(self.path.read_bytes(), self.data)

    def test_game_started_during_preparation_rejected(self):
        closed = mock.Mock(side_effect=[None, RuntimeError('Game running')])
        with self.assertRaises(RuntimeError):
            self.apply(check_closed=closed)
        self.assertEqual(self.path.read_bytes(), self.data)
        self.assertEqual(len(list((self.user/'save-restore-safety').glob('*/backup.json'))), 1)

    def test_unknown_effect_empty_primary_and_noop_rejected(self):
        for new in [[123456789]+[gems.EMPTY]*5, [gems.EMPTY]*6, self.gem['effects']]:
            self.new = new
            with self.assertRaises(ValueError):
                self.apply()
        self.assertEqual(self.path.read_bytes(), self.data)

    def test_duplicate_handles_and_truncated_data_rejected(self):
        bad = bytearray(self.data)
        struct.pack_into('<I', bad, 124, self.gem['handle'])
        for data in (bytes(bad), self.data[:-1], b'not a save'):
            with self.assertRaises(ValueError):
                gems.parse(data)

    def test_no_pattern_replacement_outside_upgrade_table(self):
        data = bytearray(self.data)
        data[0x10000:0x10028] = data[84:124]
        result = gems.rewrite(bytes(data), self.gem['handle'], self.gem['record'], self.new)
        self.assertEqual(result[0x10000:0x10028], data[84:124])

    def test_other_backup_is_untouched(self):
        backup = bytearray(self.data)
        struct.pack_into('<I', backup, 100, 126302)
        (self.folder/'backup0000').write_bytes(backup)
        result = self.apply()
        self.assertEqual(result['updated_files'], ['userdata0000'])
        self.assertEqual((self.folder/'backup0000').read_bytes(), backup)

    def test_backup_failure_never_writes(self):
        with mock.patch.object(gems.saves, '_safety_copy', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                self.apply()
        self.assertEqual(self.path.read_bytes(), self.data)

    def test_directory_publish_failure_rolls_back(self):
        real = Path.rename
        def rename(path, target):
            if path.name.startswith('.gem-stage-'):
                raise OSError('publish failed')
            return real(path, target)
        with mock.patch.object(Path, 'rename', rename):
            with self.assertRaisesRegex(OSError, 'publish failed'):
                self.apply()
        self.assertEqual(self.path.read_bytes(), self.data)
        self.assertEqual((self.folder/'backup0000').read_bytes(), self.data)

    def test_final_verification_failure_rolls_back(self):
        real = gems.saves.inventory
        def inventory(path):
            found = real(path)
            if Path(path) == self.folder and self.path.read_bytes() != self.data:
                found = {}
            return found
        with mock.patch.object(gems.saves, 'inventory', inventory):
            with self.assertRaises(OSError):
                self.apply()
        self.assertEqual(self.path.read_bytes(), self.data)

    def test_restore_lock_blocks_edit(self):
        with gems.saves._restore_lock(self.user):
            with self.assertRaises(RuntimeError):
                self.apply()

    def test_gem_changed_rejected(self):
        with self.assertRaises(ValueError):
            gems.rewrite(self.data, self.gem['handle'], '00'*40, self.new)


if __name__ == '__main__':
    unittest.main()
