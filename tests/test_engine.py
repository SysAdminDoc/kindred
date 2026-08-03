import os
import sys
import types
import unittest
from unittest.mock import patch

os.environ.setdefault("KINDRED_JWT_SECRET", "test-secret")

from app import engine


class EmbeddingModelTests(unittest.TestCase):
    def tearDown(self):
        engine._model = None
        engine._loaded_model_name = None

    def test_prefers_configured_model(self):
        loaded = []

        class FakeModel:
            def __init__(self, name):
                loaded.append(name)

        fake_module = types.SimpleNamespace(SentenceTransformer=FakeModel)
        with patch.dict(sys.modules, {"sentence_transformers": fake_module}), \
             patch.object(engine, "EMBEDDING_MODEL", "preferred"), \
             patch.object(engine, "EMBEDDING_FALLBACK_MODEL", "fallback"):
            self.assertIsInstance(engine.get_model(), FakeModel)

        self.assertEqual(loaded, ["preferred"])
        self.assertEqual(engine.get_loaded_model_name(), "preferred")

    def test_falls_back_when_preferred_model_fails(self):
        loaded = []

        class FakeModel:
            def __init__(self, name):
                loaded.append(name)
                if name == "preferred":
                    raise OSError("model unavailable")

        fake_module = types.SimpleNamespace(SentenceTransformer=FakeModel)
        with patch.dict(sys.modules, {"sentence_transformers": fake_module}), \
             patch.object(engine, "EMBEDDING_MODEL", "preferred"), \
             patch.object(engine, "EMBEDDING_FALLBACK_MODEL", "fallback"):
            self.assertIsInstance(engine.get_model(), FakeModel)

        self.assertEqual(loaded, ["preferred", "fallback"])
        self.assertEqual(engine.get_loaded_model_name(), "fallback")

    def test_mixed_embedding_dimensions_are_neutral(self):
        short = [1.0, 0.0]
        long = [1.0, 0.0, 0.0]
        self.assertEqual(engine.semantic_compatibility(short, long), 0.5)

    def test_positive_outcome_increases_weight_of_high_scoring_dimension(self):
        breakdown = {
            "personality": 90,
            "values": 50,
            "communication": 50,
            "financial": 50,
            "attachment": 50,
            "tradeoffs": 50,
            "semantic": 50,
            "dealbreakers": 50,
        }
        learned = engine.learn_weight_preferences({}, breakdown, 1.0)

        self.assertGreater(learned["personality"], engine.DEFAULT_WEIGHTS["personality"])
        self.assertAlmostEqual(sum(learned.values()), 1.0)

    def test_negative_outcome_decreases_weight_of_high_scoring_dimension(self):
        breakdown = {
            "personality": 90,
            "values": 50,
            "communication": 50,
            "financial": 50,
            "attachment": 50,
            "tradeoffs": 50,
            "semantic": 50,
            "dealbreakers": 50,
        }
        learned = engine.learn_weight_preferences({}, breakdown, 0.0)

        self.assertLess(learned["personality"], engine.DEFAULT_WEIGHTS["personality"])

    def test_manual_weights_remain_dominant_when_blended_with_learning(self):
        merged = engine.merge_weight_preferences(
            {"personality": 1.0}, {"values": 1.0}
        )

        self.assertGreater(merged["personality"], merged["values"])
        self.assertAlmostEqual(sum(merged.values()), 1.0)


if __name__ == "__main__":
    unittest.main()
