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


def aligned_field_counts(gt: list[LineItem], pred: list[LineItem], pairs: list[tuple[int,int]], family: str|None=None) -> tuple[int,int,int]:
    tp=0
    for gi,pi in pairs:
        g=collections.Counter((k,v) for k,v in gt[gi].fields if family is None or field_family(k)==family)
        p=collections.Counter((k,v) for k,v in pred[pi].fields if family is None or field_family(k)==family)
        tp+=sum((g&p).values())
    gold=sum(family is None or field_family(k)==family for row in gt for k,_ in row.fields)
    predicted=sum(family is None or field_family(k)==family for row in pred for k,_ in row.fields)
    return tp,predicted,gold


def evaluate_document(truth: Any, prediction: Any, document_id: str = "") -> dict[str, Any]:
    gt=extract_line_items(truth); pred=extract_line_items(prediction)
    matrix=[[intersection_counts(g,p)[1] for p in pred] for g in gt]
    assigned=maximum_weight_assignment(matrix)
    pairs=[(g,p) for g,p in assigned if matrix[g][p]>=MIN_WEIGHT]
    strict_pairs=[(i,i) for i in range(min(len(gt),len(pred)))]
    e0_tp,e0_pred,e0_gold=aligned_field_counts(gt,pred,strict_pairs); e0=prf(e0_tp,e0_pred,e0_gold)
    e1=e0
    matched=len(pairs); row_prf=prf(matched,len(pred),len(gt)); exact=sum(collections.Counter(gt[g].fields)==collections.Counter(pred[p].fields) for g,p in pairs)
    field_tp,field_pred,field_gold=aligned_field_counts(gt,pred,pairs); field_prf=prf(field_tp,field_pred,field_gold)
    families={}
    for family in ("item_name","item_price","quantity","unit_price"):
        values=aligned_field_counts(gt,pred,pairs,family); families[family]=prf(*values)
    critical_tp,critical_pred,critical_gold=aligned_field_counts(gt,pred,pairs,"item_price"); critical_prf=prf(critical_tp,critical_pred,critical_gold)
    strict_weight=sum(matrix[g][p] for g,p in strict_pairs) if matrix else 0.0; optimal_weight=sum(matrix[g][p] for g,p in pairs) if matrix else 0.0
    assignment_changed=any(g!=p for g,p in pairs)
    alignment_error=assignment_changed or optimal_weight>strict_weight+1e-12
    return {
        "document_id":document_id,"gt_rows":len(gt),"predicted_rows":len(pred),
        "E0_historical_flat_precision":e0[0],"E0_historical_flat_recall":e0[1],"E0_historical_flat_f1":e0[2],
        "E1_strict_row_order_precision":e1[0],"E1_strict_row_order_recall":e1[1],"E1_strict_row_order_f1":e1[2],
        "E2_line_item_precision":row_prf[0],"E2_line_item_recall":row_prf[1],"E2_line_item_f1":row_prf[2],
        "row_exact_matches":exact,"row_exact_match_rate":exact/len(gt) if gt else (1.0 if not pred else 0.0),
        "field_within_row_precision":field_prf[0],"field_within_row_recall":field_prf[1],"field_within_row_micro_f1":field_prf[2],
        "item_name_f1":families["item_name"][2],"item_price_f1":families["item_price"][2],"quantity_f1":families["quantity"][2],"unit_price_f1":families["unit_price"][2],
        "critical_monetary_row_f1":critical_prf[2],"row_alignment_error":alignment_error,
        "unmatched_gt_rows":len(gt)-matched,"spurious_predicted_rows":len(pred)-matched,
        "strict_matching_weight":strict_weight,"optimal_matching_weight":optimal_weight,
        "matches":[{"gt_index":g,"predicted_index":p,"weight":matrix[g][p],"exact":collections.Counter(gt[g].fields)==collections.Counter(pred[p].fields)} for g,p in pairs],
        "gt_items":[asdict(row) for row in gt],"predicted_items":[asdict(row) for row in pred]
    }


def aggregate(documents: list[dict[str,Any]], designation: str) -> dict[str,Any]:
    n=len(documents)
    metric_names=["E0_historical_flat_f1","E1_strict_row_order_f1","E2_line_item_f1","row_exact_match_rate","field_within_row_micro_f1","item_name_f1","item_price_f1","quantity_f1","unit_price_f1","critical_monetary_row_f1"]
    return {"designation":designation,"documents":n,"document_mean_metrics":{name:sum(float(row[name]) for row in documents)/n if n else 0 for name in metric_names},"row_alignment_failure_rate":sum(bool(row["row_alignment_error"]) for row in documents)/n if n else 0,"unmatched_gt_rows":sum(int(row["unmatched_gt_rows"]) for row in documents),"spurious_predicted_rows":sum(int(row["spurious_predicted_rows"]) for row in documents)}


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--input",type=Path,required=True); parser.add_argument("--output-dir",type=Path,required=True); parser.add_argument("--designation",required=True); args=parser.parse_args()
    payload=json.loads(args.input.read_text()); documents=[evaluate_document(row["truth"],row["prediction"],row["document_id"]) for row in payload["predictions"]]
    args.output_dir.mkdir(parents=True,exist_ok=True)
    scalar=[{k:v for k,v in row.items() if k not in {"matches","gt_items","predicted_items"}} for row in documents]
    with (args.output_dir/"document_line_item_metrics.csv").open("w",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=list(scalar[0]),lineterminator="\n"); writer.writeheader(); writer.writerows(scalar)
    (args.output_dir/"aggregate_metrics.json").write_text(json.dumps(aggregate(documents,args.designation),indent=2,sort_keys=True)+"\n")
    examples=[row for row in documents if row["row_alignment_error"] or row["unmatched_gt_rows"] or row["spurious_predicted_rows"]][:20]
    (args.output_dir/"normalized_examples.json").write_text(json.dumps({"designation":args.designation,"raw_images_published":False,"examples":examples},indent=2,sort_keys=True)+"\n")
    print(json.dumps(aggregate(documents,args.designation),sort_keys=True))


if __name__=="__main__": main()
