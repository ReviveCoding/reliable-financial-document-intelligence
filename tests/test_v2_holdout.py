import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from v2_guard import assert_input_allowed  # noqa: E402


class V2HoldoutGuardTests(unittest.TestCase):
    def state(self, directory: Path, lifecycle: str) -> Path:
        path = directory / "state.json"
        path.write_text(json.dumps({"evaluation_state": lifecycle}))
        return path

    def test_development_is_allowed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assert_input_allowed(root / "validation.jsonl", self.state(root, "V2_DEVELOPMENT"))

    def test_test_and_final_are_denied_during_development(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = self.state(root, "V2_DEVELOPMENT")
            for candidate in (root / "test.jsonl", root / "final.jsonl", root / "test" / "data.jsonl"):
                with self.assertRaises(RuntimeError):
                    assert_input_allowed(candidate, state)

    def test_locked_inputs_require_explicit_authorization(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assert_input_allowed(root / "test.jsonl", self.state(root, "V2_FINAL_EVAL_AUTHORIZED"))


if __name__ == "__main__":
    unittest.main()
