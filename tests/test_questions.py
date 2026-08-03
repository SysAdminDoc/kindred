import unittest

from app.questions import (
    BIG_FIVE_ITEMS,
    IRT_ITEM_PARAMS,
    irt_item_information,
    score_big_five,
    select_adaptive_big_five_items,
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


if __name__ == "__main__":
    unittest.main()
