import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class AnalysisProtocolTests(unittest.TestCase):
    def setUp(self): self.protocol=json.loads((ROOT/"configs/v3_1/analysis_protocol.json").read_text())
    def test_statistical_method_contract(self):
        self.assertEqual(self.protocol["bootstrap"]["replicates"],2000)
        self.assertEqual(self.protocol["minimum_support"]["headline"],20)
        self.assertEqual(self.protocol["correction"]["method"],"Benjamini-Hochberg FDR")
        self.assertTrue(self.protocol["paired_comparisons_require_identical_document_ids"])
    def test_robustness_contract(self):
        self.assertEqual(len(self.protocol["robustness"]["corruptions"]),6)
        self.assertTrue(all(len(v)==2 for v in self.protocol["robustness"]["corruptions"].values()))
        self.assertEqual(self.protocol["robustness"]["gpu_maximum_concurrent_heavy_jobs"],1)
    def test_governance_scope(self):
        self.assertTrue(self.protocol["created_before_locked_slice_results"])
        self.assertIn("CORD vendor",self.protocol["slice_families"]["prohibited_slices"])


if __name__=="__main__": unittest.main()
