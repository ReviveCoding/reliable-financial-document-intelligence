from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from scripts.v3_2.line_item_evaluation import evaluate_document, extract_line_items, field_family, flatten, maximum_weight_assignment, intersection_counts, normalize

ROOT=Path(__file__).resolve().parents[2]
PROTOCOL=json.loads((ROOT/"configs/v3_2/risk_protocol.json").read_text())
WEIGHTS=PROTOCOL["targets"]["critical_field_weights"]


def digits(value: object) -> str: return "".join(re.findall(r"\d",str(value or "")))


def scalar(value: Any, path: tuple[str,...]) -> str:
    for key in path:
        if not isinstance(value,dict): return ""
        value=value.get(key,"")
    return normalize(value) if not isinstance(value,(dict,list)) else ""


def path_error(truth: Any, prediction: Any, path: tuple[str,...]) -> tuple[int,int]:
    g=scalar(truth,path); p=scalar(prediction,path)
    if not g and not p: return 0,0
    return int(g!=p),1


def critical_targets(truth: Any, prediction: Any, line: dict[str,Any]) -> dict[str,Any]:
    numerator=denominator=0.0; document_error=False
    mapping=[("document_total",("total","total_price")),("subtotal",("sub_total","subtotal_price")),("tax",("sub_total","tax_price")),("discount",("sub_total","discount_price"))]
    for name,path in mapping:
        error,supported=path_error(truth,prediction,path)
        numerator+=error*float(WEIGHTS[name]); denominator+=supported*float(WEIGHTS[name]); document_error |= bool(error)
    gt=extract_line_items(truth); pred=extract_line_items(prediction); matrix=[[intersection_counts(g,p)[1] for p in pred] for g in gt]; pairs=[x for x in maximum_weight_assignment(matrix) if matrix[x[0]][x[1]]>=1.0] if matrix and pred else []
    matched_gt={g for g,_ in pairs}; matched_pred={p for _,p in pairs}; line_error=False
    for family,weight_name in (("item_price","item_total_price"),("unit_price","item_unit_price"),("quantity","quantity")):
        weight=float(WEIGHTS[weight_name])
        for gi,pi in pairs:
            left=collections.Counter((k,v) for k,v in gt[gi].fields if field_family(k)==family); right=collections.Counter((k,v) for k,v in pred[pi].fields if field_family(k)==family)
            supported=max(sum(left.values()),sum(right.values())); errors=supported-sum((left&right).values())
            numerator+=errors*weight; denominator+=supported*weight
            if family in {"item_price","unit_price"} and errors: line_error=True
        for gi,row in enumerate(gt):
            if gi not in matched_gt:
                count=sum(field_family(k)==family for k,_ in row.fields); numerator+=count*weight; denominator+=count*weight; line_error |= family in {"item_price","unit_price"} and count>0
        for pi,row in enumerate(pred):
            if pi not in matched_pred:
                count=sum(field_family(k)==family for k,_ in row.fields); numerator+=count*weight; denominator+=count*weight; line_error |= family in {"item_price","unit_price"} and count>0
    if line["row_alignment_error"] and any(field_family(k) in {"item_price","unit_price"} for row in gt+pred for k,_ in row.fields):
        numerator+=float(WEIGHTS["item_total_price"]); denominator+=float(WEIGHTS["item_total_price"]); line_error=True
    document_error |= line_error
    return {"document_has_critical_error":document_error,"document_has_line_item_critical_error":line_error,"document_has_row_alignment_error":bool(line["row_alignment_error"]),"weighted_critical_loss":min(1.0,numerator/denominator) if denominator else 0.0,"critical_error_weight":numerator,"critical_supported_weight":denominator}


def reconciliation(prediction: Any) -> tuple[float,int]:
    subtotal=digits(scalar(prediction,("sub_total","subtotal_price"))); tax=digits(scalar(prediction,("sub_total","tax_price"))); discount=digits(scalar(prediction,("sub_total","discount_price"))); total=digits(scalar(prediction,("total","total_price")))
    if not subtotal or not total: return 0.0,0
    expected=int(subtotal)+(int(tax) if tax else 0)-(abs(int(discount)) if discount else 0); residual=abs(expected-int(total))/max(1,abs(int(total))); return residual,int(residual>.01)


def count_predicted_fields(value: Any) -> int: return len(flatten(value))


def repeated_density(prediction: Any) -> float:
    values=[v for _,v in flatten(prediction)]; return (len(values)-len(set(values)))/len(values) if values else 0.0


def partitions(document_ids: list[str]) -> dict[str,str]:
    ordered=sorted(document_ids,key=lambda document_id:hashlib.sha256(f"{PROTOCOL['determinism']['seed']}:{document_id}".encode()).hexdigest())
    fit=round(len(ordered)*.6); selection=round(len(ordered)*.8)
    return {document_id:("FIT" if index<fit else "THRESHOLD_SELECTION" if index<selection else "INDEPENDENT_CERTIFICATION") for index,document_id in enumerate(ordered)}


FEATURES=[
    ("image_width","PRE_INFERENCE",True),("image_height","PRE_INFERENCE",True),("image_megapixels","PRE_INFERENCE",True),("aspect_ratio","PRE_INFERENCE",True),("blur","PRE_INFERENCE",True),("luminance","PRE_INFERENCE",True),("contrast","PRE_INFERENCE",True),("estimated_skew","PRE_INFERENCE",True),("edge_density","PRE_INFERENCE",True),("foreground_density","PRE_INFERENCE",True),
    ("sequence_confidence","POST_EXTRACTION",True),("predicted_field_count","POST_EXTRACTION",True),("predicted_line_item_count","POST_EXTRACTION",True),("predicted_output_length","POST_EXTRACTION",True),("schema_valid","POST_EXTRACTION",True),("parse_failure","POST_EXTRACTION",True),("missing_total","POST_EXTRACTION",True),("missing_subtotal","POST_EXTRACTION",True),("missing_tax","POST_EXTRACTION",True),("missing_discount","POST_EXTRACTION",True),("missing_any_item_price","POST_EXTRACTION",True),("reconciliation_residual","POST_EXTRACTION",True),("reconciliation_contradiction_count","POST_EXTRACTION",True),("latency_seconds","POST_EXTRACTION",True),("predicted_repeated_value_density","POST_EXTRACTION",True),("predicted_long_description","POST_EXTRACTION",True),("predicted_monetary_density","POST_EXTRACTION",True),
    ("total_field_disagreement","POST_EXTRACTION",False),("critical_field_disagreement","POST_EXTRACTION",False),("row_line_item_disagreement","POST_EXTRACTION",False),
    ("ground_truth_leaf_count","NOT_PRODUCTION_SAFE",False),("true_line_item_count","NOT_PRODUCTION_SAFE",False),("true_ocr_token_count","NOT_PRODUCTION_SAFE",False)
]


def build(split: str, output: Path) -> None:
    artifact="donut_development.json" if split=="validation" else "final_donut.json"; designation="DEVELOPMENT" if split=="validation" else "RETROSPECTIVE_LOCKED_BENCHMARK"
    predictions=json.loads((ROOT/"artifacts/v2/results"/artifact).read_text())["predictions"]
    partition_by_id=partitions([row["document_id"] for row in predictions]) if split=="validation" else {}
    canonical={r["document_id"]:r for r in csv.DictReader((ROOT/"artifacts/v3_1/data/document_evaluation_table.csv").open()) if r["model"]=="Donut" and r["split"]==split}
    rows=[]
    for source in predictions:
        doc=canonical[source["document_id"]]; pred=source["prediction"]; truth=source["truth"]; line=evaluate_document(truth,pred,source["document_id"]); target=critical_targets(truth,pred,line); menu=extract_line_items(pred); residual,contradictions=reconciliation(pred); leaves=flatten(pred); monetary=sum(field_family(k) in {"item_price","unit_price"} or any(x in k for x in ("total_price","tax_price","discount_price")) for k,_ in leaves)
        feature={
            "image_width":doc["image_width"],"image_height":doc["image_height"],"image_megapixels":doc["image_megapixels"],"aspect_ratio":doc["aspect_ratio"],"blur":doc["blur"],"luminance":doc["luminance"],"contrast":doc["contrast"],"estimated_skew":doc["estimated_skew"],"edge_density":doc["edge_density"],"foreground_density":doc["foreground_density"],
            "sequence_confidence":source.get("sequence_confidence",""),"predicted_field_count":count_predicted_fields(pred),"predicted_line_item_count":len(menu),"predicted_output_length":len(source.get("raw_sequence","")),"schema_valid":bool(source.get("schema_valid",False)),"parse_failure":not bool(source.get("schema_valid",False)),
            "missing_total":not bool(scalar(pred,("total","total_price"))),"missing_subtotal":not bool(scalar(pred,("sub_total","subtotal_price"))),"missing_tax":not bool(scalar(pred,("sub_total","tax_price"))),"missing_discount":not bool(scalar(pred,("sub_total","discount_price"))),"missing_any_item_price":any(not any(field_family(k) in {"item_price","unit_price"} for k,_ in row.fields) for row in menu) if menu else True,
            "reconciliation_residual":residual,"reconciliation_contradiction_count":contradictions,"latency_seconds":source["latency_seconds"],"predicted_repeated_value_density":repeated_density(pred),"predicted_long_description":max((len(v) for row in menu for k,v in row.fields if field_family(k)=="item_name"),default=0),"predicted_monetary_density":monetary/max(1,len(leaves)),
            "total_field_disagreement":"","critical_field_disagreement":"","row_line_item_disagreement":"",
            "ground_truth_leaf_count":doc["ground_truth_leaf_count"],"true_line_item_count":doc["line_item_count"],"true_ocr_token_count":doc["text_token_count"]
        }
        rows.append({"document_id":source["document_id"],"source_document_id":source["document_id"],"dataset":"CORD v2","split":split,"designation":designation,"development_partition":partition_by_id[source["document_id"]] if split=="validation" else "RETROSPECTIVE_ONLY",**feature,**target,"E2_line_item_f1":line["E2_line_item_f1"],"critical_monetary_row_f1":line["critical_monetary_row_f1"]})
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("w",newline="") as h: writer=csv.DictWriter(h,fieldnames=list(rows[0]),lineterminator="\n"); writer.writeheader(); writer.writerows(rows)
    dictionary=[]
    for name,tag,use in FEATURES: dictionary.append({"feature":name,"availability_tag":tag,"eligible_for_risk_model":use,"provenance":"frozen extractor output" if tag=="POST_EXTRACTION" else "image pixels before inference" if tag=="PRE_INFERENCE" else "retrospective ground truth or unavailable disagreement","missing_policy":"not used" if not use else "development median plus missing indicator"})
    for label in ["document_has_critical_error","document_has_line_item_critical_error","document_has_row_alignment_error","weighted_critical_loss"]: dictionary.append({"feature":label,"availability_tag":"NOT_PRODUCTION_SAFE","eligible_for_risk_model":False,"provenance":"evaluation target from ground truth","missing_policy":"target only"})
    with (output.parent/"risk_feature_dictionary.csv").open("w",newline="") as h: writer=csv.DictWriter(h,fieldnames=list(dictionary[0]),lineterminator="\n"); writer.writeheader(); writer.writerows(dictionary)
    summary={"designation":designation,"rows":len(rows),"partitions":dict(collections.Counter(r["development_partition"] for r in rows)),"critical_error_prevalence":sum(bool(r["document_has_critical_error"]) for r in rows)/len(rows),"line_item_critical_error_prevalence":sum(bool(r["document_has_line_item_critical_error"]) for r in rows)/len(rows),"row_alignment_error_prevalence":sum(bool(r["document_has_row_alignment_error"]) for r in rows)/len(rows),"mean_weighted_critical_loss":sum(float(r["weighted_critical_loss"]) for r in rows)/len(rows),"risk_model_eligible_features":[name for name,_,use in FEATURES if use],"forbidden_features_present_only_as_retrospective_metadata":[name for name,tag,_ in FEATURES if tag=="NOT_PRODUCTION_SAFE"]}
    (output.parent/f"{split}_risk_feature_summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n"); print(json.dumps(summary,sort_keys=True))


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--split",choices=["validation","test"],required=True); parser.add_argument("--output",type=Path,required=True); args=parser.parse_args(); build(args.split,args.output)


if __name__=="__main__": main()
