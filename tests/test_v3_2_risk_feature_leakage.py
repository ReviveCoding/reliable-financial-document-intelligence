import json
import unittest
from pathlib import Path

from scripts.v3_2.build_risk_features import FEATURES

ROOT=Path(__file__).resolve().parents[1]


class RiskFeatureLeakageTests(unittest.TestCase):
    def test_model_features_have_allowed_availability(self):
        allowed=set(json.loads((ROOT/"configs/v3_2/risk_protocol.json").read_text())["feature_policy"]["allowed_tags"])
        self.assertFalse([(name,tag) for name,tag,use in FEATURES if use and tag not in allowed])

    def test_ground_truth_features_are_excluded(self):
        protocol=json.loads((ROOT/"configs/v3_2/risk_protocol.json").read_text())
        selected={name for name,_,use in FEATURES if use}
        self.assertTrue(selected.isdisjoint(protocol["feature_policy"]["ground_truth_features_forbidden"]))

    def test_annotated_ocr_is_not_a_model_feature(self):
        selected={name.casefold() for name,_,use in FEATURES if use}
        self.assertNotIn("cord_valid_line_count",selected)
        self.assertNotIn("true_ocr_token_count",selected)

    def test_total_disagreement_not_mislabeled_line_item(self):
        entries={name:use for name,_,use in FEATURES}
        self.assertFalse(entries["row_line_item_disagreement"])
        self.assertFalse(entries["total_field_disagreement"])


if __name__=="__main__": unittest.main()
