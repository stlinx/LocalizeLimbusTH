from __future__ import annotations

import unittest
from pathlib import Path

from work.import_boss_from_wiki_html import parse_boss


RIEN_HTML = Path(r"C:\Users\kimoj\Downloads\boss\The Index Nursefather - Rien - Limbus Company Wiki.html")


@unittest.skipUnless(RIEN_HTML.exists(), "saved Rien wiki HTML is not available")
class BossWikiImporterTests(unittest.TestCase):
    def test_imports_rien_skills_stats_and_statuses(self) -> None:
        boss = parse_boss(RIEN_HTML)
        self.assertEqual(boss["name_en"], "The Index Nursefather - Rien")
        self.assertEqual(boss["level"], 85)
        self.assertEqual(boss["hp"], 4375)
        self.assertEqual(boss["defense_level"], 88)
        self.assertGreaterEqual(len(boss["skills"]), 13)
        first_skill = boss["skills"][0]
        self.assertEqual(first_skill["base_power"], 2)
        self.assertEqual(first_skill["coin_power"], 2)
        self.assertIn("Atk Weight", first_skill["attack_level_text"])
        self.assertTrue(first_skill.get("asset_path"))
        self.assertTrue(first_skill.get("description_lines"))
        self.assertTrue(first_skill.get("coin_effect_lines"))
        self.assertTrue(boss.get("passives"))
        self.assertTrue(boss["passives"][0].get("description_lines"))
        status_names = {item["source_name"] for item in boss.get("unique_statuses", [])}
        self.assertIn("Poise", status_names)
        self.assertIn("Rien's Mask", status_names)

    def test_skill_text_does_not_swallow_behavior_sections(self) -> None:
        boss = parse_boss(RIEN_HTML)
        skill_text = "\n".join(
            line
            for skill in boss["skills"]
            for line in skill.get("description_lines", []) + skill.get("coin_effect_lines", [])
        )
        self.assertNotIn("Battle Tips", skill_text)
        self.assertNotIn("Dialogue", skill_text)
        self.assertNotIn("id=\"Behavior\"", skill_text)


if __name__ == "__main__":
    unittest.main()
