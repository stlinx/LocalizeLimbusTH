from __future__ import annotations

import unittest

from backend.services import DEFAULT_DB, get_boss_profile, get_boss_turn_intent, get_status_effect, list_status_effects, search_bosses
from simulator.statuses import status_rule_for


class StatusAndBossServiceTests(unittest.TestCase):
    def test_status_search_includes_combat_rule_annotation(self) -> None:
        item = get_status_effect("Poise", DEFAULT_DB, "en")
        self.assertEqual(item["status_key"], "Breath")
        self.assertIn(item["combat_rule"]["implementation"], {"partial", "planned", "display_only"})

    def test_all_statuses_are_listable(self) -> None:
        payload = list_status_effects(DEFAULT_DB, "th", 2000)
        self.assertGreater(payload["count"], 100)
        self.assertIn("display_only", payload["implementation_counts"])

    def test_unknown_status_rule_is_display_only(self) -> None:
        rule = status_rule_for("SomeFutureStatus", "Some Future Status")
        self.assertEqual(rule["implementation"], "display_only")

    def test_lei_heng_has_structured_boss_behavior(self) -> None:
        profile = get_boss_profile("wiki_lei_heng_draft")
        behavior = profile.get("boss_behavior") or {}
        self.assertEqual(behavior.get("schema_version"), 1)
        patterns = {pattern["pattern_id"]: pattern for pattern in behavior.get("patterns", [])}
        self.assertIn("opening", patterns)
        self.assertIn("below_40_savage_replacement", patterns)
        self.assertEqual(patterns["opening"]["rows"][0]["skills"][0], "lei_heng_triple_slash")
        self.assertEqual(patterns["below_40_savage_replacement"]["boss_sp"], 30)
        replacement = patterns["below_40_savage_replacement"].get("replacement_rules", [])[0]
        self.assertEqual(replacement["replace_skill"], "lei_heng_tanglecleaver")
        self.assertEqual(replacement["with_skill"], "lei_heng_savage_tigerslayer_s_perfected_flurry_of_blades")

    def test_lei_heng_turn_intent_uses_structured_behavior(self) -> None:
        opening = get_boss_turn_intent("wiki_lei_heng_draft", turn=1, hp_percent=100)
        self.assertEqual(opening["pattern"]["pattern_id"], "opening")
        self.assertEqual(len(opening["slots"]), 6)
        self.assertEqual(opening["slots"][0]["skill_id"], "lei_heng_triple_slash")
        self.assertEqual(opening["boss_sp"], 0)

        savage = get_boss_turn_intent("wiki_lei_heng_draft", turn=8, hp_percent=35)
        self.assertEqual(savage["pattern"]["pattern_id"], "below_40_savage_replacement")
        self.assertEqual(savage["boss_sp"], 30)
        self.assertEqual(savage["slots"][0]["skill_id"], "lei_heng_savage_tigerslayer_s_perfected_flurry_of_blades")
        self.assertEqual(savage["speed_bonus"], 15)

    def test_manual_boss_fixture_search_and_profile(self) -> None:
        results = search_bosses("status dummy", 4)
        self.assertGreaterEqual(results["count"], 1)
        profile = get_boss_profile("manual_status_dummy")
        self.assertEqual(profile["boss_id"], "manual_status_dummy")
        self.assertEqual(profile["source"], "manual_fixture")


if __name__ == "__main__":
    unittest.main()
