import unittest

from scripts.v3_2.build_risk_features import critical_targets
from scripts.v3_2.line_item_evaluation import evaluate_document


def parsed(*rows): return {"menu":list(rows)}


class LineItemEvaluatorTests(unittest.TestCase):
    def check_permutation(self, truth, prediction):
        result=evaluate_document(truth,prediction); target=critical_targets(truth,prediction,result)
        self.assertEqual(result["E2_matched_field_micro_f1"],1); self.assertEqual(result["E2_row_exact_match_rate"],1)
        self.assertTrue(result["row_permutation_only"]); self.assertFalse(result["row_semantic_association_error"])
        self.assertFalse(target["document_has_critical_error"]); self.assertEqual(target["weighted_critical_loss"],0)

    def test_01_perfect_rows(self):
        value=parsed({"nm":"A","cnt":"1","price":"10"},{"nm":"B","cnt":"2","price":"20"}); result=evaluate_document(value,value)
        self.assertEqual(result["E2_matched_row_f1"],1); self.assertEqual(result["E2_matched_field_micro_f1"],1); self.assertFalse(result["row_permutation_only"])

    def test_02_swapped_row_order(self):
        self.check_permutation(parsed({"nm":"A","price":"10"},{"nm":"B","price":"20"}),parsed({"nm":"B","price":"20"},{"nm":"A","price":"10"}))

    def test_03_duplicated_identical_price(self):
        value=parsed({"nm":"A","price":"10"},{"nm":"B","price":"10"}); self.assertEqual(evaluate_document(value,value)["item_price_f1"],1)

    def test_04_missing_row(self):
        result=evaluate_document(parsed({"nm":"A","price":"10"},{"nm":"B","price":"20"}),parsed({"nm":"A","price":"10"}))
        self.assertEqual(result["unmatched_gt_rows"],1); self.assertTrue(result["row_missing_error"]); self.assertFalse(result["row_permutation_only"])

    def test_05_extra_row(self):
        result=evaluate_document(parsed({"nm":"A","price":"10"}),parsed({"nm":"A","price":"10"},{"nm":"B","price":"20"}))
        self.assertEqual(result["spurious_predicted_rows"],1); self.assertTrue(result["row_spurious_error"])

    def test_06_wrong_name_price_association(self):
        truth=parsed({"nm":"A","price":"10"},{"nm":"B","price":"20"}); pred=parsed({"nm":"A","price":"20"},{"nm":"B","price":"10"})
        result=evaluate_document(truth,pred); target=critical_targets(truth,pred,result)
        self.assertFalse(result["row_permutation_only"]); self.assertLess(result["E2_matched_field_micro_f1"],1)
        self.assertGreater(result["monetary_association_error_count"],0); self.assertTrue(target["document_has_line_item_critical_error"])

    def test_07_duplicate_descriptions(self):
        value=parsed({"nm":"coffee","price":"10"},{"nm":"coffee","price":"20"}); self.assertEqual(evaluate_document(value,value)["item_name_f1"],1)

    def test_08_missing_item_price(self):
        truth=parsed({"nm":"A","price":"10"}); pred=parsed({"nm":"A"}); result=evaluate_document(truth,pred)
        self.assertEqual(result["item_price_f1"],0); self.assertTrue(critical_targets(truth,pred,result)["document_has_critical_error"])

    def test_09_nested_split_submenu(self):
        value=parsed({"nm":"set","price":"20","sub_menu":[{"nm":"tea"},{"nm":"cake"}]}); self.assertEqual(evaluate_document(value,value)["E2_row_exact_match_rate"],1)

    def test_10_repeated_identical_rows(self):
        value=parsed({"nm":"tea","price":"10"},{"nm":"tea","price":"10"},{"nm":"tea","price":"10"}); result=evaluate_document(value,value)
        self.assertEqual(result["E2_row_exact_matches"],3); self.assertFalse(result["row_permutation_only"])

    def test_11_three_row_pure_permutation(self):
        truth=parsed({"nm":"A","price":"10"},{"nm":"B","price":"20"},{"nm":"C","price":"30"}); pred=parsed({"nm":"C","price":"30"},{"nm":"A","price":"10"},{"nm":"B","price":"20"}); self.check_permutation(truth,pred)

    def test_12_permutation_plus_wrong_price(self):
        truth=parsed({"nm":"A","price":"10"},{"nm":"B","price":"20"}); pred=parsed({"nm":"B","price":"21"},{"nm":"A","price":"10"}); result=evaluate_document(truth,pred)
        self.assertFalse(result["row_permutation_only"]); self.assertTrue(result["row_semantic_association_error"]); self.assertLess(result["item_price_f1"],1)

    def test_13_permutation_plus_missing_row(self):
        truth=parsed({"nm":"A","price":"10"},{"nm":"B","price":"20"},{"nm":"C","price":"30"}); pred=parsed({"nm":"C","price":"30"},{"nm":"A","price":"10"}); result=evaluate_document(truth,pred)
        self.assertTrue(result["row_missing_error"]); self.assertFalse(result["row_permutation_only"])

    def test_14_equal_price_ambiguous_different_descriptions(self):
        self.check_permutation(parsed({"nm":"A","price":"10"},{"nm":"B","price":"10"}),parsed({"nm":"B","price":"10"},{"nm":"A","price":"10"}))

    def test_15_exact_rows_different_numeric_ids(self):
        truth=parsed({"row_id":1,"nm":"A","price":"10"},{"row_id":2,"nm":"B","price":"20"}); pred=parsed({"row_id":99,"nm":"A","price":"10"},{"row_id":42,"nm":"B","price":"20"}); result=evaluate_document(truth,pred)
        self.assertEqual(result["E2_matched_field_micro_f1"],1); self.assertFalse(result["row_structure_failure"])


if __name__=="__main__": unittest.main()
