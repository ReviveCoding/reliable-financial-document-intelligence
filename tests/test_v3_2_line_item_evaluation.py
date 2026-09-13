import unittest

from scripts.v3_2.line_item_evaluation import evaluate_document


def parsed(*rows): return {"menu":list(rows)}


class LineItemEvaluatorTests(unittest.TestCase):
    def test_01_perfect_rows(self):
        value=parsed({"nm":"A","cnt":"1","price":"10"},{"nm":"B","cnt":"2","price":"20"})
        result=evaluate_document(value,value)
        self.assertEqual(result["E2_line_item_f1"],1); self.assertEqual(result["field_within_row_micro_f1"],1)

    def test_02_swapped_row_order(self):
        truth=parsed({"nm":"A","price":"10"},{"nm":"B","price":"20"}); pred=parsed({"nm":"B","price":"20"},{"nm":"A","price":"10"})
        result=evaluate_document(truth,pred)
        self.assertEqual(result["E2_line_item_f1"],1); self.assertEqual(result["field_within_row_micro_f1"],1); self.assertLess(result["E1_strict_row_order_f1"],1)

    def test_03_duplicated_identical_price(self):
        value=parsed({"nm":"A","price":"10"},{"nm":"B","price":"10"})
        self.assertEqual(evaluate_document(value,value)["critical_monetary_row_f1"],1)

    def test_04_missing_row(self):
        result=evaluate_document(parsed({"nm":"A","price":"10"},{"nm":"B","price":"20"}),parsed({"nm":"A","price":"10"}))
        self.assertEqual(result["unmatched_gt_rows"],1); self.assertLess(result["E2_line_item_recall"],1)

    def test_05_extra_row(self):
        result=evaluate_document(parsed({"nm":"A","price":"10"}),parsed({"nm":"A","price":"10"},{"nm":"B","price":"20"}))
        self.assertEqual(result["spurious_predicted_rows"],1); self.assertLess(result["E2_line_item_precision"],1)

    def test_06_correct_values_assigned_to_wrong_row(self):
        truth=parsed({"nm":"A","price":"10"},{"nm":"B","price":"20"}); pred=parsed({"nm":"A","price":"20"},{"nm":"B","price":"10"})
        result=evaluate_document(truth,pred)
        self.assertLess(result["field_within_row_micro_f1"],1)
        self.assertTrue(result["row_alignment_error"])
        self.assertGreater(result["optimal_matching_weight"],result["strict_matching_weight"])

    def test_07_duplicate_description(self):
        value=parsed({"nm":"coffee","price":"10"},{"nm":"coffee","price":"20"})
        self.assertEqual(evaluate_document(value,value)["item_name_f1"],1)

    def test_08_missing_item_price(self):
        result=evaluate_document(parsed({"nm":"A","price":"10"}),parsed({"nm":"A"}))
        self.assertEqual(result["critical_monetary_row_f1"],0)

    def test_09_split_sub_menu(self):
        value=parsed({"nm":"set","price":"20","sub_menu":[{"nm":"tea"},{"nm":"cake"}]})
        self.assertEqual(evaluate_document(value,value)["row_exact_match_rate"],1)

    def test_10_repeated_identical_item_values(self):
        value=parsed({"nm":"tea","price":"10"},{"nm":"tea","price":"10"},{"nm":"tea","price":"10"})
        result=evaluate_document(value,value)
        self.assertEqual(result["row_exact_matches"],3); self.assertEqual(result["E2_line_item_f1"],1)


if __name__=="__main__": unittest.main()
