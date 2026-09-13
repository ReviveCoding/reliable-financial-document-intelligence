from __future__ import annotations

import argparse
import collections
import csv
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = json.loads((ROOT / "configs/v3_2/risk_protocol.json").read_text())
WEIGHTS = PROTOCOL["line_item_evaluation"]["matching_field_weights"]
MIN_WEIGHT = float(PROTOCOL["line_item_evaluation"]["match_acceptance_minimum_weight"])
IDENTITY_KEYS = {"row_id", "group_id", "sub_group_id"}


def normalize(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().casefold())


def flatten(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in IDENTITY_KEYS:
                continue
            result.extend(flatten(item, f"{prefix}.{key}" if prefix else key))
    elif isinstance(value, list):
        for item in value:
            result.extend(flatten(item, prefix))
    elif value is not None and normalize(value):
        result.append((prefix, normalize(value)))
    return result


def field_family(path: str) -> str:
    key = path.rsplit(".", 1)[-1].casefold()
    if key in {"nm", "name", "item_name", "description"}: return "item_name"
    if key in {"cnt", "count", "quantity", "qty"}: return "quantity"
    if key in {"unitprice", "unit_price", "unit_price_value"}: return "unit_price"
    if key in {"price", "item_price", "total_price", "subtotal_price"}: return "item_price"
    return "other"


def matching_weight(path: str) -> float:
    key = path.rsplit(".", 1)[-1].casefold()
    return float(WEIGHTS.get(key, WEIGHTS["etc"]))


@dataclass(frozen=True)
class LineItem:
    position: int
    fields: tuple[tuple[str, str], ...]
    row_id: str = ""
    group_id: str = ""
    sub_group_id: str = ""


def extract_line_items(parsed: Any) -> list[LineItem]:
    menu = parsed.get("menu", []) if isinstance(parsed, dict) else []
    if isinstance(menu, dict): menu = [menu]
    if not isinstance(menu, list): return []
    output=[]
    for position, row in enumerate(menu):
        if not isinstance(row, dict):
            row = {"value": row}
        output.append(LineItem(position, tuple(flatten(row)), *(normalize(row.get(k, "")) for k in ("row_id", "group_id", "sub_group_id"))))
    return output


def intersection_counts(a: LineItem, b: LineItem) -> tuple[int, float]:
    left=collections.Counter(a.fields); right=collections.Counter(b.fields); shared=left & right
    count=sum(shared.values()); weighted=sum(matching_weight(path)*n for (path,_),n in shared.items())
    return count, weighted


def maximum_weight_assignment(matrix: list[list[float]]) -> list[tuple[int, int]]:
    """Deterministic Hungarian assignment for a rectangular maximum-weight matrix."""
    if not matrix or not matrix[0]: return []
    original_rows, original_cols=len(matrix),len(matrix[0]); size=max(original_rows,original_cols)
    padded=[row+[0.0]*(size-original_cols) for row in matrix]+[[0.0]*size for _ in range(size-original_rows)]
    cost=[[-value for value in row] for row in padded]
    u=[0.0]*(size+1); v=[0.0]*(size+1); p=[0]*(size+1); way=[0]*(size+1)
    for i in range(1,size+1):
        p[0]=i; j0=0; minimum=[float("inf")]*(size+1); used=[False]*(size+1)
        while True:
            used[j0]=True; i0=p[j0]; delta=float("inf"); j1=0
            for j in range(1,size+1):
                if used[j]: continue
                current=cost[i0-1][j-1]-u[i0]-v[j]
                if current < minimum[j]: minimum[j]=current; way[j]=j0
                if minimum[j] < delta: delta=minimum[j]; j1=j
            for j in range(size+1):
                if used[j]: u[p[j]]+=delta; v[j]-=delta
                else: minimum[j]-=delta
            j0=j1
            if p[j0]==0: break
        while True:
            j1=way[j0]; p[j0]=p[j1]; j0=j1
            if j0==0: break
    assignment=[]
    for j in range(1,size+1):
        i=p[j]
        if 1<=i<=original_rows and j<=original_cols: assignment.append((i-1,j-1))
    return sorted(assignment)


def prf(tp: int, predicted: int, gold: int) -> tuple[float,float,float]:
    precision=tp/predicted if predicted else (1.0 if gold==0 else 0.0)
    recall=tp/gold if gold else (1.0 if predicted==0 else 0.0)
    f1=2*precision*recall/(precision+recall) if precision+recall else 0.0
    return precision,recall,f1


def row_fields(rows: list[LineItem]) -> list[tuple[str,str]]:
    return [field for row in rows for field in row.fields]


def aligned_field_counts(gt: list[LineItem], pred: list[LineItem], pairs: list[tuple[int,int]], family: str|None=None, matched_only: bool=False) -> tuple[int,int,int]:
    tp=0
    for gi,pi in pairs:
        g=collections.Counter((k,v) for k,v in gt[gi].fields if family is None or field_family(k)==family)
        p=collections.Counter((k,v) for k,v in pred[pi].fields if family is None or field_family(k)==family)
        tp+=sum((g&p).values())
    gt_scope=[gt[g] for g,_ in pairs] if matched_only else gt
    pred_scope=[pred[p] for _,p in pairs] if matched_only else pred
    gold=sum(family is None or field_family(k)==family for row in gt_scope for k,_ in row.fields)
    predicted=sum(family is None or field_family(k)==family for row in pred_scope for k,_ in row.fields)
    return tp,predicted,gold


def path_occurrence_counts(gt: list[LineItem], pred: list[LineItem]) -> tuple[int,int,int]:
    """Reproduce v3.1 menu path/occurrence semantics with row identity discarded."""
    gold: dict[str,list[str]]=collections.defaultdict(list); predicted: dict[str,list[str]]=collections.defaultdict(list)
    for row in gt:
        for path,value in row.fields: gold[path].append(value)
    for row in pred:
        for path,value in row.fields: predicted[path].append(value)
    tp=0
    for path in set(gold)|set(predicted):
        tp+=sum(left==right for left,right in zip(gold[path],predicted[path]))
    return tp,sum(map(len,predicted.values())),sum(map(len,gold.values()))


def monetary_association_errors(gt: list[LineItem], pred: list[LineItem], pairs: list[tuple[int,int]]) -> int:
    """Count price-to-description bindings contradicted by another predicted row."""
    count=0
    for gi,pi in pairs:
        gt_names={v for k,v in gt[gi].fields if field_family(k)=="item_name"}
        pred_names={v for k,v in pred[pi].fields if field_family(k)=="item_name"}
        shared_money={(field_family(k),v) for k,v in gt[gi].fields if field_family(k) in {"item_price","unit_price"}} & {(field_family(k),v) for k,v in pred[pi].fields if field_family(k) in {"item_price","unit_price"}}
        if shared_money and gt_names and pred_names and not (gt_names & pred_names):
            if any(gt_names & {v for k,v in other.fields if field_family(k)=="item_name"} for j,other in enumerate(pred) if j!=pi):
                count+=len(shared_money)
    return count


def family_error_breakdown(gt: list[LineItem], pred: list[LineItem], pairs: list[tuple[int,int]], family: str) -> tuple[int,int,int]:
    missing=spurious=incorrect=0; matched_gt={g for g,_ in pairs}; matched_pred={p for _,p in pairs}
    for gi,pi in pairs:
        left=collections.Counter((k,v) for k,v in gt[gi].fields if field_family(k)==family)
        right=collections.Counter((k,v) for k,v in pred[pi].fields if field_family(k)==family)
        common=left&right; left-=common; right-=common
        paired=min(sum(left.values()),sum(right.values())); incorrect+=paired
        missing+=sum(left.values())-paired; spurious+=sum(right.values())-paired
    missing+=sum(field_family(k)==family for i,row in enumerate(gt) if i not in matched_gt for k,_ in row.fields)
    spurious+=sum(field_family(k)==family for i,row in enumerate(pred) if i not in matched_pred for k,_ in row.fields)
    return missing,spurious,incorrect


def evaluate_document(truth: Any, prediction: Any, document_id: str = "") -> dict[str, Any]:
    gt=extract_line_items(truth); pred=extract_line_items(prediction)
    matrix=[[intersection_counts(g,p)[1] for p in pred] for g in gt]
    assigned=maximum_weight_assignment(matrix)
    pairs=[(g,p) for g,p in assigned if matrix[g][p]>=MIN_WEIGHT]
    strict_pairs=[(i,i) for i in range(min(len(gt),len(pred)))]
    e0=prf(*path_occurrence_counts(gt,pred))
    e1=prf(*aligned_field_counts(gt,pred,strict_pairs))
    matched=len(pairs); row_prf=prf(matched,len(pred),len(gt)); exact=sum(collections.Counter(gt[g].fields)==collections.Counter(pred[p].fields) for g,p in pairs)
    field_prf=prf(*aligned_field_counts(gt,pred,pairs,matched_only=True))
    families={}
    for family in ("item_name","item_price","quantity","unit_price"):
        values=aligned_field_counts(gt,pred,pairs,family,matched_only=True); families[family]=prf(*values)
    strict_weight=sum(matrix[g][p] for g,p in strict_pairs) if matrix else 0.0; optimal_weight=sum(matrix[g][p] for g,p in pairs) if matrix else 0.0
    assignment_changed=any(g!=p for g,p in pairs)
    unmatched_gt=len(gt)-matched; spurious_pred=len(pred)-matched
    permutation_only=assignment_changed and exact==matched and matched==len(gt)==len(pred)
    semantic_error=assignment_changed and not permutation_only and exact<matched
    missing_error=unmatched_gt>0; spurious_error=spurious_pred>0
    structure_failure=semantic_error or missing_error or spurious_error
    association_errors=monetary_association_errors(gt,pred,pairs)
    price_missing,price_spurious,price_incorrect=family_error_breakdown(gt,pred,pairs,"item_price")
    return {
        "document_id":document_id,"gt_rows":len(gt),"predicted_rows":len(pred),
        "E0_path_occurrence_precision":e0[0],"E0_path_occurrence_recall":e0[1],"E0_path_occurrence_f1":e0[2],
        "E1_positional_row_precision":e1[0],"E1_positional_row_recall":e1[1],"E1_positional_row_f1":e1[2],
        "E2_matched_rows":matched,"E2_matched_row_precision":row_prf[0],"E2_matched_row_recall":row_prf[1],"E2_matched_row_f1":row_prf[2],
        "E2_row_exact_matches":exact,"E2_row_exact_match_rate":exact/len(gt) if gt else (1.0 if not pred else 0.0),
        "E2_matched_field_precision":field_prf[0],"E2_matched_field_recall":field_prf[1],"E2_matched_field_micro_f1":field_prf[2],
        "item_name_f1":families["item_name"][2],"item_price_f1":families["item_price"][2],"quantity_f1":families["quantity"][2],"unit_price_f1":families["unit_price"][2],
        "row_permutation_only":permutation_only,"row_semantic_association_error":semantic_error,
        "row_missing_error":missing_error,"row_spurious_error":spurious_error,"row_structure_failure":structure_failure,
        "monetary_association_error_count":association_errors,
        "missing_item_price_count":price_missing,"spurious_item_price_count":price_spurious,"incorrect_item_price_count":price_incorrect+association_errors,
        "unmatched_gt_rows":unmatched_gt,"spurious_predicted_rows":spurious_pred,
        "strict_matching_weight":strict_weight,"optimal_matching_weight":optimal_weight,
        "matches":[{"gt_index":g,"predicted_index":p,"weight":matrix[g][p],"exact":collections.Counter(gt[g].fields)==collections.Counter(pred[p].fields)} for g,p in pairs],
        "gt_items":[asdict(row) for row in gt],"predicted_items":[asdict(row) for row in pred]
    }


def aggregate(documents: list[dict[str,Any]], designation: str) -> dict[str,Any]:
    n=len(documents)
    metric_names=["E0_path_occurrence_f1","E1_positional_row_f1","E2_matched_row_f1","E2_matched_field_micro_f1","E2_row_exact_match_rate","item_name_f1","item_price_f1","quantity_f1","unit_price_f1"]
    return {"designation":designation,"documents":n,"document_mean_metrics":{name:sum(float(row[name]) for row in documents)/n if n else 0 for name in metric_names},"row_permutation_only_rate":sum(bool(row["row_permutation_only"]) for row in documents)/n if n else 0,"row_semantic_association_error_rate":sum(bool(row["row_semantic_association_error"]) for row in documents)/n if n else 0,"row_missing_error_rate":sum(bool(row["row_missing_error"]) for row in documents)/n if n else 0,"row_spurious_error_rate":sum(bool(row["row_spurious_error"]) for row in documents)/n if n else 0,"row_structure_failure_rate":sum(bool(row["row_structure_failure"]) for row in documents)/n if n else 0,"unmatched_gt_rows":sum(int(row["unmatched_gt_rows"]) for row in documents),"spurious_predicted_rows":sum(int(row["spurious_predicted_rows"]) for row in documents)}


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--input",type=Path,required=True); parser.add_argument("--output-dir",type=Path,required=True); parser.add_argument("--designation",required=True); args=parser.parse_args()
    payload=json.loads(args.input.read_text()); documents=[evaluate_document(row["truth"],row["prediction"],row["document_id"]) for row in payload["predictions"]]
    args.output_dir.mkdir(parents=True,exist_ok=True)
    scalar=[{k:v for k,v in row.items() if k not in {"matches","gt_items","predicted_items"}} for row in documents]
    with (args.output_dir/"document_line_item_metrics.csv").open("w",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=list(scalar[0]),lineterminator="\n"); writer.writeheader(); writer.writerows(scalar)
    (args.output_dir/"aggregate_metrics.json").write_text(json.dumps(aggregate(documents,args.designation),indent=2,sort_keys=True)+"\n")
    examples=[row for row in documents if row["row_permutation_only"] or row["row_structure_failure"]][:20]
    (args.output_dir/"normalized_examples.json").write_text(json.dumps({"designation":args.designation,"raw_images_published":False,"examples":examples},indent=2,sort_keys=True)+"\n")
    print(json.dumps(aggregate(documents,args.designation),sort_keys=True))


if __name__=="__main__": main()
