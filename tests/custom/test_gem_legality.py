"""Whole-variant tests based on documented table examples and rare exceptions."""
import sys
from pathlib import Path
import unittest

LOCAL=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(LOCAL/'scripts'))
sys.path.insert(0,str(LOCAL/'launcher'))
import bbport_gem_legality as rules
E=rules.EMPTY


class TableTests(unittest.TestCase):
    def test_cursed_droplet_independent_rolls(self):
        gem={'shape':63,'effects':[126515,47217,E,E,E,E]}
        self.assertEqual(rules.match(gem,gem['effects']),'lantern-hamlet')
        for primary in (126515,126516,126517):
            for rank in (15,16,17):
                for base in (28200,34200,36200,41200,44200,47200):
                    self.assertEqual(rules.validate(gem,[primary,base+rank,E,E,E,E]),'lantern-hamlet')
        for invalid in ([126619,41217,E,E,E,E],[126517,41214,E,E,E,E],
                        [126514,41217,E,E,E,E],[126517,17120,41217,E,E,E]):
            with self.assertRaises(ValueError):rules.validate(gem,invalid)

    def test_all_documented_droplet_tiers(self):
        gem={'shape':63,'effects':[126515,47217,E,E,E,E]}
        for rank,area in ((6,'frontier'),(7,'frontier'),(13,'mensis'),(14,'mensis'),
                          (15,'hamlet'),(16,'hamlet'),(17,'hamlet')):
            self.assertEqual(rules.validate(gem,[126500+rank,41200+rank,E,E,E,E]),'lantern-'+area)
        with self.assertRaises(ValueError):rules.validate(dict(gem,shape=8),[126517,41217,E,E,E,E])

    def test_percent_display_missing_catalog_symbol(self):
        import bbport_gem_save as backend
        self.assertIn('+19%',backend.effect_text(126513))
        self.assertIn('+3%',backend.effect_text(41217))
        self.assertNotIn('%',backend.effect_text(47217))

    def gem(self,shape=1,source=124002,profile=None):
        value={'source':0x80000000|source,'effects':[126307,48107,E,E,E,E],'shape':shape}
        if profile:value['table_profile']=profile
        return value

    def test_272_has_no_positive_secondary(self):
        gem=self.gem(profile='watcher-physical')
        self.assertEqual(rules.validate(gem,[126619,41218,E,E,E,E]),'watcher-physical')
        with self.assertRaises(ValueError):rules.validate(gem,[126619,17120,41218,E,E,E])

    def test_abyssal_248_can_have_flat_15(self):
        gem=self.gem(profile='abyssal-physical')
        self.assertEqual(rules.validate(gem,[126520,17120,41218,E,E,E]),'abyssal-physical')
        with self.assertRaises(ValueError):rules.validate(gem,[126520,41218,E,E,E,E])

    def test_different_source_and_old_rank_do_not_lock_conversion(self):
        gem=self.gem(source=124002,profile='abyssal-heavy')
        self.assertEqual(rules.validate(gem,[129520,17120,41218,E,E,E]),'abyssal-heavy')
        self.assertTrue(rules.policy(gem)['editable'])

    def test_current_fixed_gem_can_select_table_type(self):
        gem=self.gem()
        self.assertIn('watcher-physical',rules.available(gem))
        gem['table_profile']='watcher-physical'
        self.assertTrue(rules.policy(gem)['editable'])

    def test_unknown_original_source_can_select_table_type(self):
        gem=self.gem(source=1234567,profile='watcher-physical')
        rules.validate(gem,[126619,41218,E,E,E,E])

    def test_not_in_table_does_not_claim_illegal(self):
        gem=self.gem()
        self.assertIn('保持不变',rules.policy(gem)['reason'])
        self.assertEqual(rules.candidates(gem,0),())

    def test_rare_out_of_effect_is_not_banned(self):
        gem=self.gem(shape=4,profile='watcher-blood')
        rules.validate(gem,[122619,41218,E,E,E,E])

    def test_oos_radial_triangle_waning_are_supported(self):
        for shape in (1,2,4):
            rules.validate(self.gem(shape=shape,profile='watcher-physical'),[126619,41218,E,E,E,E])

    def test_chalice_watcher_droplet_and_circle_are_not_fabricated(self):
        for shape in (8,63):
            with self.assertRaises(ValueError):rules.validate(self.gem(shape=shape,profile='watcher-physical'),[126619,41218,E,E,E,E])

    def test_shotgun_circle_and_oos_are_supported(self):
        for shape in (1,2,4,8):
            rules.validate(self.gem(shape=shape,profile='shotgun-blood'),[122618,41218,E,E,E,E])

    def test_documented_coffin_droplet_is_valid_without_a_curse(self):
        p=rules.PROFILES['coffin-droplet']
        self.assertEqual(p['rating'],11)
        self.assertTrue(p['sheet_rows'])
        rules.validate(self.gem(shape=63,profile='coffin-droplet'),[26411,E,E,E,E,E])
        with self.assertRaises(ValueError):rules.validate(self.gem(shape=63,profile='coffin-droplet'),[26411,41218,E,E,E,E])

    def test_uncursed_coffin_variant_cannot_be_given_extra_secondary(self):
        p=rules.PROFILES['coffin-physical'];values=list(p['default'])
        rules.validate(self.gem(profile='coffin-physical'),values)
        values[1]=17120
        with self.assertRaises(ValueError):rules.validate(self.gem(profile='coffin-physical'),values)

    def test_fixed_secondary_duplicate_exception(self):
        p=rules.PROFILES['spirit-double-poorman']
        first,second=p['default'][:2]
        self.assertEqual(rules.EXCLUSIONS[first],rules.EXCLUSIONS[second])
        rules.validate(self.gem(profile='spirit-double-poorman'),list(p['default']))

    def test_double_effect_not_allowed_on_random_watcher(self):
        p=rules.PROFILES['spirit-double-poorman']
        with self.assertRaises(ValueError):rules.validate(self.gem(profile='watcher-poorman'),list(p['default']))

    def test_nourishing_cannot_roll_attack_down(self):
        gem=self.gem(profile='abyssal-nourishing')
        base=list(rules.PROFILES['abyssal-nourishing']['default'])
        self.assertNotIn(28218,rules.candidates(gem,2,base))
        base[2]=28218
        with self.assertRaises(ValueError):rules.validate(gem,base)

    def test_half_curse_not_replaced_by_normal_curse(self):
        gem=self.gem(profile='abyssal-cold')
        p=rules.PROFILES['abyssal-cold']
        self.assertEqual(p['default'][2],41119)
        rules.validate(gem,list(p['default']))
        bad=list(p['default']);bad[2]=41218
        with self.assertRaises(ValueError):rules.validate(gem,bad)

    def test_fixed_secondary_strengths_not_mixed(self):
        gem=self.gem(profile='brainsucker')
        rules.validate(gem,[126219,14419,41218,E,E,E])
        with self.assertRaises(ValueError):rules.validate(gem,[126219,14417,41218,E,E,E])

    def test_global_maxima_from_different_enemies_cannot_be_spliced(self):
        gem=self.gem(profile='abyssal-heavy')
        self.assertNotIn(14419,rules.candidates(gem,1,[129520,17120,41218,E,E,E]))
        with self.assertRaises(ValueError):rules.validate(gem,[129520,14419,41218,E,E,E])

    def test_runes_unknown_and_extra_slots_are_rejected(self):
        gem=self.gem(profile='watcher-physical')
        for values in ([1100000,41218,E,E,E,E],[126619,41218,17120,E,E,E],[65511,41218,E,E,E,E]):
            with self.assertRaises(ValueError):rules.validate(gem,values)

    def test_madman_secondary_189_not_15(self):
        p=rules.PROFILES['madman-physical']
        rules.validate(self.gem(profile='madman-physical'),list(p['default']))
        bad=list(p['default']);bad[1]=17120
        with self.assertRaises(ValueError):rules.validate(self.gem(profile='madman-physical'),bad)

    def test_all_defaults_are_whole_valid_combinations(self):
        for key,profile in rules.PROFILES.items():
            for shape in profile['shapes']:
                rules.validate(self.gem(shape=shape,profile=key),list(profile['default']))

    def test_all_candidate_curses_pass_the_same_save_gate(self):
        for key,profile in rules.PROFILES.items():
            gem=self.gem(profile=key);values=list(profile['default'])
            for index in range(6):
                for effect in rules.candidates(gem,index,values):
                    changed=list(values);changed[index]=effect
                    rules.validate(gem,changed)


if __name__=='__main__':unittest.main()
