import math
import unittest

from scratch.embusen_study import compute_foot_positions


class KibaDachiTests(unittest.TestCase):
    def test_same_stance_with_different_facing_and_lead(self):
        history = compute_foot_positions(
            [
                dict(stance="kiba_dachi", lead="both", facing="N", turn="0"),
                dict(stance="kiba_dachi", lead="right", facing="E", turn="right_90"),
                dict(stance="kiba_dachi", lead="left", facing="W", turn="left_180"),
                dict(stance="kiba_dachi", lead="left", facing="W", turn="0"),
                dict(stance="kiba_dachi", lead="both", facing="N", turn="right_90"),
            ]
        )

        for step in history[1:]:
            self.assertEqual(step["l_pos"], history[0]["l_pos"])
            self.assertEqual(step["r_pos"], history[0]["r_pos"])
            self.assertEqual(step["stance_heading"], 0)
            self.assertEqual(step["pivot_type"], "stationary")

    def test_side_facing_convention_applies_at_other_headings(self):
        history = compute_foot_positions(
            [
                dict(stance="kiba_dachi", lead="right", facing="N", turn="0"),
                dict(stance="kiba_dachi", lead="left", facing="S", turn="left_180"),
            ]
        )

        self.assertEqual(history[0]["stance_heading"], 270)
        self.assertEqual(history[1]["l_pos"], history[0]["l_pos"])
        self.assertEqual(history[1]["r_pos"], history[0]["r_pos"])

    def test_actual_stance_reorientation_is_not_stationary(self):
        history = compute_foot_positions(
            [
                dict(stance="kiba_dachi", lead="both", facing="N", turn="0"),
                dict(stance="kiba_dachi", lead="both", facing="E", turn="right_90"),
            ]
        )

        self.assertEqual(history[1]["stance_heading"], 90)
        self.assertNotEqual(history[1]["l_pos"], history[0]["l_pos"])
        self.assertTrue(history[1]["ambiguity"])

    def test_crossover_entry_retains_kiba_geometry(self):
        history = compute_foot_positions(
            [
                dict(stance="kosa_dachi", lead="right", facing="E", turn="right_90"),
                dict(stance="kiba_dachi", lead="both", facing="N", turn="left_90"),
            ]
        )

        left, right = history[1]["l_pos"], history[1]["r_pos"]
        self.assertTrue(history[1]["ambiguity"])
        self.assertEqual(left[1], right[1])
        self.assertEqual(left[2], right[2])
        self.assertTrue(math.isclose(right[0] - left[0], 72))


class StanceOrientationTests(unittest.TestCase):
    def test_kokutsu_angles_follow_catalog_in_world_coordinates(self):
        for lead, expected_angles in [("left", (90, 180)), ("right", (0, 90))]:
            with self.subTest(lead=lead):
                [step] = compute_foot_positions(
                    [
                        dict(
                            stance="kokutsu_dachi",
                            lead=lead,
                            facing="E",
                            turn="right_90",
                        )
                    ]
                )
                self.assertEqual(
                    (step["l_pos"][2] % 360, step["r_pos"][2] % 360), expected_angles
                )

    def test_template_geometry_is_applied_even_to_ambiguous_slides(self):
        history = compute_foot_positions(
            [
                dict(stance="zenkutsu_dachi", lead="left", facing="W", turn="left_90"),
                dict(stance="kokutsu_dachi", lead="left", facing="W", turn="0"),
            ]
        )
        left, right = history[1]["l_pos"], history[1]["r_pos"]
        self.assertAlmostEqual(right[1], left[1])
        self.assertAlmostEqual(right[0] - left[0], 72)

    def test_catalog_only_stance_has_correct_contact_and_angle(self):
        [step] = compute_foot_positions(
            [dict(stance="hizakutsu", lead="left", facing="N", turn="0")]
        )
        self.assertEqual(step["l_pos"][2:], [0, "full"])
        self.assertEqual(step["r_pos"][2:], [0, "ball"])

    def test_unspecified_crossover_lead_is_flagged(self):
        [step] = compute_foot_positions(
            [dict(stance="kosa_dachi", lead="both", facing="N", turn="0")]
        )
        self.assertIn("No catalog footprint", step["ambiguity"])
        self.assertEqual(step["r_pos"][3], "ball")
