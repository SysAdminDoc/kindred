import unittest

from app.questions import (
    BIG_FIVE_ITEMS,
    IRT_ITEM_PARAMS,
    build_regional_norm_table,
    calibrate_big_five,
    irt_item_information,
    score_big_five,
    select_adaptive_big_five_items,
    select_next_adaptive_question,
)


class AdaptiveQuestionTests(unittest.TestCase):
    def test_question_bank_exceeds_one_thousand_items(self):
        self.assertGreaterEqual(len(BIG_FIVE_ITEMS), 1000)
        self.assertEqual(len(BIG_FIVE_ITEMS), len(IRT_ITEM_PARAMS))

    def test_selection_is_highest_information_and_excludes_seen_items(self):
        excluded = {item[0] for item in BIG_FIVE_ITEMS[:20]}
        selected = select_adaptive_big_five_items(excluded_ids=excluded, limit=30)
        scores = [irt_item_information(item[0]) for item in selected]

        self.assertEqual(len(selected), 30)
        self.assertEqual(len({item[0] for item in selected}), 30)
        self.assertTrue(all(item[0] not in excluded for item in selected))
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_generated_items_feed_existing_big_five_scoring(self):
        item_id, _, trait, _ = next(
            item for item in BIG_FIVE_ITEMS if item[0].startswith("irt_")
        )
        scores = score_big_five({item_id: 5})
        self.assertIn(trait, scores)
        self.assertGreater(scores[trait], 0.5)

    def test_active_selector_shifts_to_undercovered_dimensions(self):
        personality_answers = {
            item[0]: 3 for item in BIG_FIVE_ITEMS[:8]
        }
        next_question = select_next_adaptive_question(
            answers={"big_five_answers": personality_answers},
            asked_ids=set(personality_answers),
        )

        self.assertIsNotNone(next_question)
        self.assertNotEqual(next_question["dimension"], "personality")
        self.assertGreater(next_question["expected_information_gain"], 0)
        self.assertIn("field", next_question)

    def test_regional_calibration_requires_a_cohort_and_centers_scores(self):
        profiles = [
            {
                "country": "USA",
                "big_five_raw": {"openness": 0.7},
            }
            for _ in range(20)
        ]
        norms = build_regional_norm_table(profiles)
        calibrated = calibrate_big_five(
            {"openness": 0.5}, "US", norms
        )

        self.assertEqual(norms["US"]["sample_size"], 20)
        self.assertLess(calibrated["openness"], 0.5)
        self.assertEqual(
            calibrate_big_five({"openness": 0.5}, "CA", norms)["openness"],
            0.5,
        )


if __name__ == "__main__":
    unittest.main()
