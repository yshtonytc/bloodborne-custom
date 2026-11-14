"""Stable scheduling decisions, including previews and failed/missing packages."""
import importlib.util
from pathlib import Path
import unittest

ROOT = next(parent for parent in Path(__file__).resolve().parents
            if (parent / 'custom/auto_update.py').is_file())
spec = importlib.util.spec_from_file_location('auto_update', ROOT / 'custom/auto_update.py')
auto = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auto)


class AutoUpdateTests(unittest.TestCase):
    def test_current_release_needs_no_build(self):
        self.assertEqual(auto.plan({'tag':'1.2.3'}, {'tag_name':'1.2.3'}, {})['build'], 'true')
        self.assertEqual(auto.plan({'tag':'1.2.3'}, {'tag_name':'1.2.3'}, {'id':1})['build'], 'false')

    def test_new_stable_is_merged(self):
        result = auto.plan({'tag':'windows-v1.2.3'}, {'tag_name':'windows-v1.2.4'}, None)
        self.assertEqual(result['sync_tag'], 'windows-v1.2.4')

    def test_preview_never_downgraded(self):
        result = auto.plan({'tag':'0.17.1','prerelease':True}, {'tag_name':'0.16.1'}, {'id':1})
        self.assertEqual(result['build'], 'false')

    def test_promoted_preview_refreshes_metadata(self):
        result = auto.plan({'tag':'0.17.1','prerelease':True}, {'tag_name':'0.17.1'}, None)
        self.assertEqual(result['sync_tag'], '0.17.1')

    def test_preview_or_draft_cannot_enter_stable_channel(self):
        for flag in ('draft', 'prerelease'):
            with self.assertRaises(ValueError):
                auto.plan({'tag':'1.2.3'}, {'tag_name':'1.2.4',flag:True}, None)
            with self.assertRaises(ValueError):
                auto.plan({'tag':'1.2.3'}, {'tag_name':'1.2.3'}, {flag:True})


if __name__ == '__main__':
    unittest.main()
