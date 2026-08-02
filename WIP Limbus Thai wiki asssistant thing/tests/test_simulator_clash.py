from __future__ import annotations

import unittest

from simulator.clash import ClashInput, SkillSpec, clash_probability, heads_chance, simulate_clash_sequence, skill_distribution


class ClashSimulatorTests(unittest.TestCase):
    def test_heads_chance_clamps_to_limbus_sp_range(self) -> None:
        self.assertAlmostEqual(heads_chance(0), 0.5)
        self.assertAlmostEqual(heads_chance(45), 0.95)
        self.assertAlmostEqual(heads_chance(-45), 0.05)
        self.assertAlmostEqual(heads_chance(99), 0.95)

    def test_plus_coin_distribution(self) -> None:
        skill = SkillSpec(id="test", name="Test", base_power=4, coins=(3, 3))
        distribution = skill_distribution(skill, sp=0)
        self.assertAlmostEqual(distribution[4], 0.25)
        self.assertAlmostEqual(distribution[7], 0.5)
        self.assertAlmostEqual(distribution[10], 0.25)

    def test_minus_coin_distribution(self) -> None:
        skill = SkillSpec(id="test", name="Minus", base_power=20, coins=(-8,))
        distribution = skill_distribution(skill, sp=45)
        self.assertAlmostEqual(distribution[12], 0.95)
        self.assertAlmostEqual(distribution[20], 0.05)

    def test_clash_probability(self) -> None:
        attacker = {10: 1.0}
        defender = {8: 0.25, 10: 0.25, 12: 0.5}
        result = clash_probability(attacker, defender)
        self.assertAlmostEqual(result["attacker_win"], 0.25)
        self.assertAlmostEqual(result["tie"], 0.25)
        self.assertAlmostEqual(result["defender_win"], 0.5)



    def test_deterministic_sequence_breaks_losing_coins(self) -> None:
        attacker = ClashInput(SkillSpec(id="a", name="A", base_power=3, coins=(4, 4, 4)), label="Attacker")
        defender = ClashInput(SkillSpec(id="d", name="D", base_power=5, coins=(2, 2, 2)), label="Defender")
        result = simulate_clash_sequence(attacker, defender, "HHH HHH HHH", "TTT TT TT")
        self.assertEqual(result["winner"], "attacker")
        self.assertEqual(len(result["rounds"]), 3)
        self.assertEqual(result["defender"]["coins_remaining"], 0)
        self.assertEqual(result["attacker"]["attack_coins"], 3)


    def test_tied_round_rerolls_until_a_coin_loses(self) -> None:
        attacker = ClashInput(SkillSpec(id="a", name="A", base_power=5, coins=(1,)), label="Attacker")
        defender = ClashInput(SkillSpec(id="d", name="D", base_power=5, coins=(1,)), label="Defender")
        result = simulate_clash_sequence(attacker, defender, "T H", "T T")
        self.assertEqual(result["rounds"][0]["loser"], "tie")
        self.assertEqual(result["rounds"][0]["attacker_coins_remaining"], 1)
        self.assertEqual(result["rounds"][0]["defender_coins_remaining"], 1)
        self.assertEqual(result["winner"], "attacker")
        self.assertEqual(len(result["rounds"]), 2)

    def test_tied_rounds_cancel_after_99(self) -> None:
        attacker = ClashInput(SkillSpec(id="a", name="A", base_power=5, coins=(1,)), label="Attacker")
        defender = ClashInput(SkillSpec(id="d", name="D", base_power=5, coins=(1,)), label="Defender")
        result = simulate_clash_sequence(attacker, defender, " ".join(["T"] * 120), " ".join(["T"] * 120))
        self.assertEqual(result["winner"], "clash_cancelled")
        self.assertEqual(len(result["rounds"]), 99)
        self.assertEqual(result["attacker"]["attack_coins"], 0)
        self.assertEqual(result["defender"]["attack_coins"], 0)

    def test_deterministic_sequence_attacker_loses_coin(self) -> None:
        attacker = ClashInput(SkillSpec(id="a", name="A", base_power=3, coins=(2, 2)), label="Attacker")
        defender = ClashInput(SkillSpec(id="d", name="D", base_power=8, coins=(1,)), label="Defender")
        result = simulate_clash_sequence(attacker, defender, "TT", "T")
        self.assertEqual(result["winner"], "defender")
        self.assertEqual(result["rounds"][0]["loser"], "attacker")
        self.assertEqual(result["attacker"]["coins_remaining"], 0)

if __name__ == "__main__":
    unittest.main()
