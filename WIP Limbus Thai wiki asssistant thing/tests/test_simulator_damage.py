from __future__ import annotations

import unittest

from simulator.damage import DamageInput, calculate_damage, damage_type_modifier, offense_defense_modifier, resistance_modifier


class DamageSimulatorTests(unittest.TestCase):
    def test_resistance_modifier_matches_wiki_examples(self) -> None:
        self.assertAlmostEqual(resistance_modifier(1.5), 0.5)
        self.assertAlmostEqual(resistance_modifier(0.75), -0.125)
        self.assertAlmostEqual(resistance_modifier(0.5), -0.25)
        self.assertAlmostEqual(resistance_modifier(2.0), 1.0)

    def test_stagger_overrides_damage_type_resistance_modifier(self) -> None:
        self.assertAlmostEqual(damage_type_modifier(0.5, stagger_level=1), 1.0)
        self.assertAlmostEqual(damage_type_modifier(2.0, stagger_level=2), 1.5)

    def test_offense_defense_uses_diminishing_return_formula(self) -> None:
        self.assertAlmostEqual(offense_defense_modifier(66, 60), 6 / 31)
        self.assertAlmostEqual(offense_defense_modifier(60, 66), -6 / 31)

    def test_damage_formula_combines_static_and_dynamic_groups(self) -> None:
        result = calculate_damage(
            DamageInput(
                coin_roll=40,
                offense_level=66,
                defense_level=60,
                damage_type_resistance=1.5,
                sin_resistance=0.75,
                critical=True,
                dynamic_modifier=0.2,
            )
        )
        static = 0.5 - 0.125 + (6 / 31) + 0.2
        self.assertEqual(result["final_damage"], int(40 * (1 + static) * 1.2))

    def test_damage_has_minimum_coin_floor(self) -> None:
        result = calculate_damage(DamageInput(coin_roll=40, dynamic_modifier=-10, damage_type_resistance=0.0))
        self.assertEqual(result["final_damage"], 2)


if __name__ == "__main__":
    unittest.main()
