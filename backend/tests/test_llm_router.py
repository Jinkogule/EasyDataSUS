import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from llm.router import get_llm, get_model_identifier


class LlmRouterTests(unittest.TestCase):
    def test_deepseek_model_uses_environment_override(self):
        with patch.dict(os.environ, {"OLLAMA_MODEL": "deepseek-coder:test-tag"}):
            self.assertEqual("deepseek-coder:test-tag", get_model_identifier("deepseek-local"))
            self.assertEqual("deepseek-coder:test-tag", get_llm("deepseek-local").model)

    def test_deepseek_model_has_runnable_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual("deepseek-coder:6.7b-base-q4_K_M", get_model_identifier("deepseek-local"))


if __name__ == "__main__":
    unittest.main()
