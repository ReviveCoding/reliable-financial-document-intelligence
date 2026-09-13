from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

import cv2
import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.tree import DecisionTreeClassifier, export_text


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts/v3_1"
PROTOCOL = json.loads((ROOT / "configs/v3_1/analysis_protocol.json").read_text())
RNG_SEED = PROTOCOL["bootstrap"]["seed"]
REPS = PROTOCOL["bootstrap"]["replicates"]
REVISION = "7f0115a4b758a71d6473b8d085751692da2fef98"
DATA = Path(os.environ["RFDI_DATA_ROOT"]) / "processed/cord_v2" / REVISION


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(rows[0]) if rows else []
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def norm(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().casefold())


def money(value: object) -> str:
    return "".join(re.findall(r"\d", str(value or "")))


def flatten(value: object, prefix: str = "") -> list[tuple[str, str]]:
    rows = []
    if isinstance(value, dict):
        for key, item in value.items():
            rows += flatten(item, f"{prefix}.{key}" if prefix else key)
    elif isinstance(value, list):
        for item in value:
            rows += flatten(item, prefix)
    elif value is not None:
        rows.append((prefix, norm(value)))
    return rows


def depth(value: object) -> int:
    if isinstance(value, dict):
        return 1 + max((depth(item) for item in value.values()), default=0)
    if isinstance(value, list):
        return 1 + max((depth(item) for item in value), default=0)
    return 0


def quality(path: str) -> dict[str, float]:
    image = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise RuntimeError(path)
    _, foreground = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(foreground > 0))
    skew = 0.0
    if len(coords) > 10:
        skew = float(cv2.minAreaRect(coords[:, ::-1].astype(np.float32))[-1])
        skew = skew - 90 if skew > 45 else skew
    return {
        "blur": float(cv2.Laplacian(image, cv2.CV_64F).var()),
        "luminance": float(image.mean()),
        "contrast": float(image.std()),
        "estimated_skew": abs(skew),
        "edge_density": float((cv2.Canny(image, 100, 200) > 0).mean()),
        "foreground_density": float((foreground > 0).mean()),
    }


def metadata(split: str) -> dict[str, dict[str, object]]:
    result = {}
    for line in (DATA / f"{split}.jsonl").read_text().splitlines():
        row = json.loads(line)
        gt = row["ground_truth"]
        parsed = gt["gt_parse"]
        words = [w for group in gt.get("valid_line", []) for w in group.get("words", [])]
        tokens = [str(w["text"]) for w in words]
        size = gt["meta"]["image_size"]
        width, height = int(size["width"]), int(size["height"])
        mp = width * height / 1_000_000
        fields = flatten(parsed)
        paths = [path for path, _ in fields]
        categories = [str(group.get("category", "")).casefold() for group in gt.get("valid_line", [])]
        result[row["document_id"]] = {
            "ground_truth": parsed,
            "image_path": row["pages"][0]["image_path"],
            "ground_truth_leaf_count": len(fields),
            "line_item_count": len(parsed.get("menu", [])) if isinstance(parsed.get("menu", []), list) else int(bool(parsed.get("menu"))),
            "text_token_count": len(tokens),
            "document_text_length": sum(len(token) for token in tokens),
            "ocr_box_count": len(words),
            "image_width": width,
            "image_height": height,
            "aspect_ratio": width / height,
            "image_megapixels": mp,
            "text_density": len(tokens) / mp,
            "numeric_token_density": sum(bool(re.search(r"\d", token)) for token in tokens) / max(1, len(tokens)),
            "monetary_field_count": sum(any(term in path for term in ("price", "tax", "total")) for path in paths),
            "monetary_field_density": sum(any(term in path for term in ("price", "tax", "total")) for path in paths) / max(1, len(paths)),
            "hierarchy_depth": depth(parsed),
            "subtotal_present": any("subtotal_price" in path for path in paths),
            "tax_present": any("tax_price" in path for path in paths),
            "discount_present": any("discount" in path for path in paths),
            "total_present": any(path == "total.total_price" for path in paths),
            "total_amount": float(money(parsed.get("total", {}).get("total_price")) or 0),
            **quality(row["pages"][0]["image_path"]),
        }
    return result


def criticality(path: str) -> str:
    for level, paths in PROTOCOL["field_criticality"].items():
        if level == "unmapped_policy":
            continue
        if path in paths:
            return level
    return PROTOCOL["field_criticality"]["unmapped_policy"]


def family(path: str) -> str:
    for name, paths in PROTOCOL["field_families"].items():
        if path in paths:
            return name
    if re.search(r"(?:cnt|num|price|tax|total)", path):
        return "other_numeric"
    return "free_text"


def field_rows(document_id: str, split: str, prediction: object, truth: object) -> list[dict[str, object]]:
    gold = defaultdict(list)
    pred = defaultdict(list)
    for path, value in flatten(truth): gold[path].append(value)
    for path, value in flatten(prediction): pred[path].append(value)
    rows = []
    for path in sorted(set(gold) | set(pred)):
        count = max(len(gold[path]), len(pred[path]))
        for index in range(count):
            g = gold[path][index] if index < len(gold[path]) else ""
            p = pred[path][index] if index < len(pred[path]) else ""
            rows.append({
                "document_id": document_id, "dataset": "CORD v2", "split": split,
                "model": "Donut", "field_path": path, "field_family": family(path),
                "criticality": criticality(path), "occurrence": index, "truth": g,
                "prediction": p, "truth_present": bool(g), "prediction_present": bool(p),
                "exact_match": bool(g) and g == p,
            })
    return rows


def reconciliation_failure(prediction: dict[str, object]) -> bool:
    subtotal = prediction.get("sub_total", {})
    total = prediction.get("total", {})
    if not isinstance(subtotal, dict) or not isinstance(total, dict): return False
    s, t, x = (money(subtotal.get(k)) for k in ("subtotal_price", "tax_price", "discount_price"))
    z = money(total.get("total_price"))
    if not s or not z: return False
    expected = int(s) + (int(t) if t else 0) - (abs(int(x)) if x else 0)
    return abs(expected - int(z)) > max(1, round(int(z) * 0.01))


def build_tables() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    metas = {split: metadata(split) for split in ("validation", "test")}
    docs, fields = [], []
    for split, artifact in (("validation", "donut_development.json"), ("test", "final_donut.json")):
        data = json.loads((ROOT / "artifacts/v2/results" / artifact).read_text())
        for row in data["predictions"]:
            meta = metas[split][row["document_id"]]
            total_truth = meta["ground_truth"].get("total", {}).get("total_price")
            total_pred = row.get("prediction", {}).get("total", {}).get("total_price")
            recon = reconciliation_failure(row.get("prediction", {}))
            evaluated_fields = field_rows(row["document_id"], split, row["prediction"], row["truth"])
            critical_error = any(
                not item["exact_match"] and item["criticality"] == "critical_monetary"
                for item in evaluated_fields
            )
            docs.append({
                "document_id": row["document_id"], "dataset": "CORD v2", "split": split,
                "model": "Donut", "prediction_source": f"artifacts/v2/results/{artifact}",
                **{k: v for k, v in meta.items() if k not in ("ground_truth", "image_path")},
                "number_extracted_fields": row["leaf_predicted"], "document_exact": row["leaf_f1"] == 1,
                "leaf_precision": row["leaf_true_positive"] / max(1, row["leaf_predicted"]),
                "leaf_recall": row["leaf_true_positive"] / max(1, row["leaf_gold"]),
                "leaf_f1": row["leaf_f1"], "total_exact": money(total_truth) == money(total_pred) if total_truth else "",
                "total_value_present": bool(total_pred), "confidence": row.get("sequence_confidence", ""),
                "calibrated_confidence": "", "rfdi_risk_score": "", "schema_failure": not row.get("schema_valid", False),
                "reconciliation_failure": recon, "model_disagreement_score": "", "routing_decision": "",
                "critical_error": critical_error, "latency_seconds": row["latency_seconds"], "corruption": "clean", "severity": "none",
            })
            fields += evaluated_fields
    paddle = json.loads((ROOT / "artifacts/v2/results/final_paddleocr.json").read_text())
    donut_test = {r["document_id"]: r for r in docs if r["model"] == "Donut" and r["split"] == "test"}
    for row in paddle["predictions"]:
        meta = metas["test"][row["document_id"]]
        exact = money(row["total_truth"]) == money(row["total_prediction"]) if row["total_truth"] else ""
        donut_total = donut_test[row["document_id"]]["total_exact"]
        docs.append({
            "document_id": row["document_id"], "dataset": "CORD v2", "split": "test", "model": "PP-OCRv5 + rules",
            "prediction_source": "artifacts/v2/results/final_paddleocr.json", **{k: v for k, v in meta.items() if k not in ("ground_truth", "image_path")},
            "number_extracted_fields": int(bool(row["total_prediction"])), "document_exact": "", "leaf_precision": "", "leaf_recall": "", "leaf_f1": "",
            "total_exact": exact, "total_value_present": bool(row["total_prediction"]), "confidence": row.get("mean_confidence", ""), "calibrated_confidence": "",
            "rfdi_risk_score": "", "schema_failure": False, "reconciliation_failure": "", "model_disagreement_score": float(exact != donut_total),
            "routing_decision": "", "critical_error": "", "latency_seconds": row["latency_seconds"], "corruption": "clean", "severity": "none",
        })
    native = json.loads((ROOT / "artifacts/v2/results/paddleocr_vl_development.json").read_text())
    served = json.loads((ROOT / "artifacts/v3/serving/paddleocr_vllm_comparison.json").read_text())
    for model, source, data in (("PaddleOCR-VL native", "artifacts/v2/results/paddleocr_vl_development.json", native), ("PaddleOCR-VL Docker/vLLM", "artifacts/v3/serving/paddleocr_vllm_comparison.json", served)):
        for row in data["predictions"]:
            meta = metas["validation"][row["document_id"]]
            docs.append({
                "document_id": row["document_id"], "dataset": "CORD v2", "split": "validation", "model": model, "prediction_source": source,
                **{k: v for k, v in meta.items() if k not in ("ground_truth", "image_path")}, "number_extracted_fields": "", "document_exact": "",
                "leaf_precision": "", "leaf_recall": row["leaf_value_recall"], "leaf_f1": "", "total_exact": "", "total_value_present": row["total_value_present"],
                "confidence": "", "calibrated_confidence": "", "rfdi_risk_score": "", "schema_failure": "", "reconciliation_failure": "",
                "model_disagreement_score": "", "routing_decision": "", "critical_error": "", "latency_seconds": row["latency_seconds"], "corruption": "clean", "severity": "none",
            })
    write_csv(OUT / "data/document_evaluation_table.csv", docs)
    write_csv(OUT / "data/field_evaluation_table.csv", fields)
    return docs, fields


def percentile_ci(values: list[float], seed: int) -> tuple[float, float]:
    if not values: return math.nan, math.nan
    rng = np.random.default_rng(seed); a=np.asarray(values,float)
    samples=[float(a[rng.integers(0,len(a),len(a))].mean()) for _ in range(REPS)]
    return float(np.quantile(samples,.025)), float(np.quantile(samples,.975))


def wilson(success: int, n: int) -> tuple[float, float]:
    if not n: return math.nan, math.nan
    z=1.95996398454; p=success/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return c-h,c+h


def band(value: float, cuts: list[float]) -> str:
    return "low" if value <= cuts[0] else "mid" if value <= cuts[1] else "high"


def slicing(docs: list[dict[str, object]]) -> None:
    test=[r for r in docs if r["model"]=="Donut" and r["split"]=="test"]
    cuts=PROTOCOL["cutpoint_derivation"]["values"]
    mapping={"ground_truth_leaf_count":"ground_truth_leaf_count","line_item_count":"line_item_count","ocr_token_count":"text_token_count","document_text_length":"document_text_length","image_megapixels":"image_megapixels","text_density_tokens_per_megapixel":"text_density","blur":"blur","contrast":"contrast","luminance":"luminance","edge_density":"edge_density","foreground_density":"foreground_density","monetary_field_density":"monetary_field_density","total_amount":"total_amount"}
    slice_defs=[]
    for protocol_name,column in mapping.items():
        for label in ("low","mid","high"):
            ids={r["document_id"] for r in test if band(float(r[column]),cuts[protocol_name])==label}
            slice_defs.append((protocol_name,label,ids))
    for column in ("total_present","subtotal_present","tax_present","discount_present"):
        for label,value in (("present",True),("absent",False)):
            slice_defs.append((column,label,{r["document_id"] for r in test if bool(r[column])==value}))
    slice_defs += [("simple_vs_multi_line_item","simple",{r["document_id"] for r in test if int(r["line_item_count"])<=1}),("simple_vs_multi_line_item","multi",{r["document_id"] for r in test if int(r["line_item_count"])>1})]
    metrics=[]
    for metric in ("leaf_f1","total_exact"):
        metric_test = [r for r in test if r[metric] != ""]
        overall=mean(float(r[metric]) for r in metric_test)
        for idx,(family_name,label,ids) in enumerate(slice_defs):
            rows=[r for r in metric_test if r["document_id"] in ids]; vals=[float(r[metric]) for r in rows]
            if not vals: continue
            lo,hi=wilson(sum(vals),len(vals)) if metric=="total_exact" else percentile_ci(vals,RNG_SEED+idx)
            comp=[float(r[metric]) for r in metric_test if r["document_id"] not in ids]
            p=1.0
            if comp:
                rng=np.random.default_rng(RNG_SEED+1000+idx); observed=mean(vals)-mean(comp); a=np.array(vals); b=np.array(comp)
                extreme = 0
                for _ in range(REPS):
                    boot_delta=float(rng.choice(a,len(a),replace=True).mean()-rng.choice(b,len(b),replace=True).mean())
                    extreme += abs(boot_delta-observed) >= abs(observed)
                p=(1+extreme)/(REPS+1)
            support=len(vals); designation="headline" if support>=20 else "exploratory" if support>=10 else "insufficient-support"
            threshold=PROTOCOL["practical_significance"]["absolute_f1_delta" if metric=="leaf_f1" else "absolute_binary_rate_delta"]
            metrics.append({"slice_family":family_name,"slice":label,"support_n":support,"metric":metric,"value":mean(vals),"overall_reference":overall,"absolute_delta":mean(vals)-overall,"relative_delta":(mean(vals)-overall)/overall if overall else "","ci95_low":lo,"ci95_high":hi,"p_value":p,"q_value":"","practical_significance":abs(mean(vals)-overall)>=threshold,"statistical_significance":False,"designation":designation})
    order=sorted(range(len(metrics)),key=lambda i:float(metrics[i]["p_value"])); running=1.0
    for rank,i in reversed(list(enumerate(order,1))):
        running=min(running,float(metrics[i]["p_value"])*len(metrics)/rank); metrics[i]["q_value"]=running; metrics[i]["statistical_significance"]=running<=.05
    write_csv(OUT/"slicing/slice_metrics.csv",metrics)
    eligible=[r for r in metrics if r["designation"]!="insufficient-support"]
    write_csv(OUT/"slicing/worst_slices.csv",sorted(eligible,key=lambda r:float(r["absolute_delta"]))[:20])
    quality_names={"blur","contrast","luminance","edge_density","foreground_density","image_megapixels"}
    write_csv(OUT/"slicing/image_quality_slices.csv",[r for r in metrics if r["slice_family"] in quality_names])

    pp={r["document_id"]:r for r in docs if r["model"]=="PP-OCRv5 + rules" and r["split"]=="test"}; pairs=[]
    eligible_ids={r["document_id"] for r in test if r["total_exact"] != "" and pp[r["document_id"]]["total_exact"] != ""}
    for name,label,ids in [("all","all",eligible_ids)]+[(a,b,c & eligible_ids) for a,b,c in slice_defs if a=="ground_truth_leaf_count"]:
        subset=[r for r in test if r["document_id"] in ids]; a=np.array([float(r["total_exact"]) for r in subset]); b=np.array([float(pp[r["document_id"]]["total_exact"]) for r in subset]); rng=np.random.default_rng(RNG_SEED); boot=[]
        for _ in range(REPS):
            take=rng.integers(0,len(a),len(a)); boot.append(float((a[take]-b[take]).mean()))
        pairs.append({"slice_family":name,"slice":label,"support_n":len(a),"metric":"total_exact","donut":float(a.mean()),"ppocr_rules":float(b.mean()),"paired_delta":float((a-b).mean()),"ci95_low":float(np.quantile(boot,.025)),"ci95_high":float(np.quantile(boot,.975)),"practical_significance":abs(float((a-b).mean()))>=.05,"identical_document_ids":True})
    write_csv(OUT/"slicing/pairwise_model_deltas.csv",pairs)
    dist=Counter(band(float(r["ground_truth_leaf_count"]),cuts["ground_truth_leaf_count"]) for r in test); weights={k:v/len(test) for k,v in dist.items()}
    eligible_test=[r for r in test if r["document_id"] in eligible_ids]; eligible_pp=[pp[i] for i in eligible_ids]
    dist=Counter(band(float(r["ground_truth_leaf_count"]),cuts["ground_truth_leaf_count"]) for r in eligible_test); weights={k:v/len(eligible_test) for k,v in dist.items()}
    per={m:{k:mean(float(r["total_exact"]) for r in rows if band(float(r["ground_truth_leaf_count"]),cuts["ground_truth_leaf_count"])==k) for k in weights} for m,rows in {"Donut":eligible_test,"PP-OCRv5 + rules":eligible_pp}.items()}
    raw={"Donut":mean(float(r["total_exact"]) for r in eligible_test),"PP-OCRv5 + rules":mean(float(r["total_exact"]) for r in eligible_pp)}; standardized={m:sum(weights[k]*v for k,v in values.items()) for m,values in per.items()}
    write_json(OUT/"slicing/mix_shift_analysis.json",{"experiment_id":"V3.1-E04","slice":"ground_truth_leaf_count","reference_distribution":weights,"raw_performance":raw,"per_slice_performance":per,"standardized_performance":standardized,"ranking_reversal":sorted(raw,key=raw.get)!=sorted(standardized,key=standardized.get),"interpretation":"Paired models use identical document IDs and therefore identical slice composition."})


def errors(fields: list[dict[str, object]], docs: list[dict[str, object]]) -> None:
    taxonomy=json.loads((ROOT/"configs/v3_1/error_taxonomy.json").read_text())["categories"]
    output=[]
    for row in fields:
        if row["exact_match"]: continue
        g,p=str(row["truth"]),str(row["prediction"]); category="UNCLASSIFIED"
        if g and not p: category="missing field"
        elif p and not g: category="spurious field"
        elif money(g) and money(g)==money(p): category="numeric normalization"
        elif g in p or p in g: category="partial string mismatch"
        elif g and p: category="incorrect value"
        output.append({**row,"error_type":category,"severity_weight":{"critical_monetary":10,"medium_impact":5,"low_impact_descriptive":2}[str(row["criticality"])]})
    for row in docs:
        if row["model"]=="Donut" and row["schema_failure"]: output.append({"document_id":row["document_id"],"dataset":"CORD v2","split":row["split"],"model":"Donut","field_path":"","field_family":"","criticality":"medium_impact","occurrence":"","truth":"","prediction":"","truth_present":"","prediction_present":"","exact_match":False,"error_type":"schema failure","severity_weight":5})
        if row["model"]=="Donut" and row["reconciliation_failure"]: output.append({"document_id":row["document_id"],"dataset":"CORD v2","split":row["split"],"model":"Donut","field_path":"","field_family":"","criticality":"critical_monetary","occurrence":"","truth":"","prediction":"","truth_present":"","prediction_present":"","exact_match":False,"error_type":"reconciliation contradiction","severity_weight":10})
    write_csv(OUT/"errors/error_level_dataset.csv",output)
    freq=Counter((r["error_type"] for r in output if r["split"]=="test")); total=sum(freq.values()); rows=[{"error_type":k,"frequency":freq.get(k,0),"fraction":freq.get(k,0)/total if total else 0,"definition":taxonomy[k]} for k in sorted(taxonomy,key=lambda k:(-freq.get(k,0),k))]; write_csv(OUT/"errors/error_frequency.csv",rows)
    weighted=defaultdict(float)
    for r in output:
        if r["split"]=="test": weighted[r["error_type"]]+=float(r["severity_weight"])
    write_csv(OUT/"errors/severity_weighted_frequency.csv",[{"error_type":k,"weighted_frequency":weighted.get(k,0)} for k in sorted(taxonomy,key=lambda k:(-weighted.get(k,0),k))])
    families=[]
    for name in sorted({str(r["field_family"]) for r in fields}):
        rows=[r for r in fields if r["split"]=="test" and r["field_family"]==name]; tp=sum(bool(r["exact_match"]) for r in rows); gold=sum(bool(r["truth_present"]) for r in rows); pred=sum(bool(r["prediction_present"]) for r in rows); precision=tp/pred if pred else 0; recall=tp/gold if gold else 0
        families.append({"field_family":name,"support_gold":gold,"support_predicted":pred,"true_positive":tp,"precision":precision,"recall":recall,"f1":2*precision*recall/(precision+recall) if precision+recall else 0,"exact_match_rate":tp/len(rows) if rows else 0,"errors":len(rows)-tp})
    write_csv(OUT/"errors/field_family_metrics.csv",families)


def calibration_and_risk(docs: list[dict[str, object]]) -> None:
    dev=[r for r in docs if r["model"]=="Donut" and r["split"]=="validation"]; test=[r for r in docs if r["model"]=="Donut" and r["split"]=="test"]
    xdev=np.array([float(r["confidence"]) for r in dev]); ydev=np.array([float(r["document_exact"]) for r in dev]); xt=np.array([float(r["confidence"]) for r in test]); yt=np.array([float(r["document_exact"]) for r in test])
    iso=IsotonicRegression(out_of_bounds="clip").fit(xdev,ydev); pi=iso.predict(xt)
    logits=np.log(np.clip(xdev,1e-6,1-1e-6)/(1-np.clip(xdev,1e-6,1-1e-6))); grid=np.geomspace(.05,20,300); losses=[-np.mean(ydev*np.log(np.clip(1/(1+np.exp(-logits/t)),1e-6,1-1e-6))+(1-ydev)*np.log(np.clip(1-1/(1+np.exp(-logits/t)),1e-6,1-1e-6))) for t in grid]; temp=float(grid[int(np.argmin(losses))]); pt=1/(1+np.exp(-np.log(np.clip(xt,1e-6,1-1e-6)/(1-np.clip(xt,1e-6,1-1e-6)))/temp))
    def met(p):
        e=[]
        for lo in np.linspace(0,1,10,endpoint=False):
            sel=(p>=lo)&(p<lo+.1)
            if sel.any(): e.append((float(sel.mean()),abs(float(p[sel].mean()-yt[sel].mean()))))
        lr=LogisticRegression().fit(np.log(np.clip(p,1e-6,1-1e-6)/(1-np.clip(p,1e-6,1-1e-6))).reshape(-1,1),yt)
        return {"ece":sum(w*d for w,d in e),"mce":max((d for _,d in e),default=0),"brier":brier_score_loss(yt,p),"slope":float(lr.coef_[0][0]),"intercept":float(lr.intercept_[0])}
    cal={"experiment_id":"V3.1-E05","model":"Donut","target":"document exact leaf extraction","fit":"CORD validation (100)","evaluation":"CORD locked test (100)","temperature":temp,"metrics":{"raw":met(xt),"temperature_scaling":met(pt),"isotonic":met(pi)},"critical_field_calibration":{"status":"INSUFFICIENT_OUTCOME_VARIATION","reason":"Only one total-field error exists in the locked test."}}
    write_json(OUT/"calibration/calibration_metrics.json",cal)
    rel=[]
    for method,p in (("raw",xt),("temperature_scaling",pt),("isotonic",pi)):
        for i,lo in enumerate(np.linspace(0,1,10,endpoint=False)):
            sel=(p>=lo)&(p<lo+.1)
            if sel.any(): rel.append({"method":method,"bin":i,"support_n":int(sel.sum()),"mean_confidence":float(p[sel].mean()),"accuracy":float(yt[sel].mean())})
    write_csv(OUT/"calibration/reliability_bins.csv",rel)
    pp={r["document_id"]:r for r in docs if r["model"]=="PP-OCRv5 + rules" and r["split"]=="test"}; critical=np.array([bool(r["critical_error"]) for r in test],float); docerr=1-yt
    disagreement=np.array([float(r["total_exact"]!=pp[r["document_id"]]["total_exact"]) for r in test])
    conflict=np.array([float(r["reconciliation_failure"]) for r in test])
    scores={"raw_confidence":1-xt,"calibrated_confidence":1-pi,"model_disagreement":disagreement,"confidence_plus_reconciliation":np.minimum(1,1-xt+.3*conflict)}
    # Exact repository formula from src/rfdi/risk/scoring.py with criticality=5,
    # no unavailable OOD signal, genuine reconciliation conflict and disagreement.
    scores["rfdi_composite_risk"]=np.minimum(1,np.maximum(0,1-xt+.3*conflict+.2*disagreement))
    rows=[]; costs=PROTOCOL["business_risk"]["base_costs"]
    for policy,score in scores.items():
        order=np.argsort(-score)
        for budget in PROTOCOL["review_budget_operating_points"]:
            n=round(len(test)*budget); review=set(order[:n]); auto=[i for i in range(len(test)) if i not in review]; captured=sum(critical[list(review)]); total=critical.sum(); residual=sum(docerr[auto])/max(1,len(auto)); false_accept=sum(critical[auto])/max(1,len(auto)); expected=(n*costs["human_review"]+sum(docerr[auto])*costs["medium_impact_error"]+sum(critical[auto])*costs["unsafe_automatic_acceptance"])/len(test)
            rows.append({"policy":policy,"review_budget":budget,"review_rate":n/len(test),"automation_coverage":len(auto)/len(test),"selective_risk":residual,"critical_false_accept_rate":false_accept,"critical_error_capture":captured/total if total else 1,"residual_weighted_risk":(sum(docerr[auto])*5+sum(critical[auto])*10)/len(test),"normalized_expected_cost":expected})
    write_csv(OUT/"selective_risk/review_budget_metrics.csv",rows)
    curve=[]
    for policy,score in scores.items():
        order=np.argsort(score); risks=[]
        for n in range(1,len(test)+1): risks.append(float(docerr[order[:n]].mean()))
        for n,risk in enumerate(risks,1): curve.append({"policy":policy,"coverage":n/len(test),"selective_risk":risk})
        write_json(OUT/"selective_risk"/f"{policy}_summary.json",{"aurc":mean(risks),"risk_at_coverage":{str(c):risks[max(0,round(c*len(test))-1)] for c in PROTOCOL["risk_coverage_reporting_points"]}})
    write_csv(OUT/"selective_risk/risk_coverage_curve.csv",curve)
    frontier=[]
    for scenario,mults in {"base":{"human_review":1,"critical_field_error":1},**PROTOCOL["business_risk"]["sensitivity_multipliers"]}.items():
        for row in rows:
            cost=row["review_rate"]*costs["human_review"]*mults["human_review"]+row["critical_false_accept_rate"]*costs["critical_field_error"]*mults["critical_field_error"]
            frontier.append({"scenario":scenario,**row,"sensitivity_cost":cost})
    write_csv(OUT/"business/policy_frontier.csv",frontier)


def discovery_and_drift(docs: list[dict[str, object]]) -> None:
    test=[r for r in docs if r["model"]=="Donut" and r["split"]=="test"]
    names=["image_width","image_height","aspect_ratio","image_megapixels","blur","luminance","contrast","estimated_skew","edge_density","foreground_density"]
    x=np.array([[float(r[n]) for n in names] for r in test]); y=np.array([not bool(r["document_exact"]) for r in test],int)
    tree=DecisionTreeClassifier(max_depth=3,min_samples_leaf=20,random_state=RNG_SEED,class_weight="balanced"); cv=StratifiedKFold(5,shuffle=True,random_state=RNG_SEED); scores=cross_val_score(tree,x,y,cv=cv,scoring="balanced_accuracy"); tree.fit(x,y)
    write_json(OUT/"discovery/failure_tree.json",{"label":"EXPLORATORY_DISCOVERED_SLICE","features":names,"max_depth":3,"minimum_leaf_support":20,"cross_validation_balanced_accuracy_mean":float(scores.mean()),"cross_validation_scores":scores.tolist(),"rules":export_text(tree,feature_names=names).splitlines(),"leakage_exclusions":["document_id","ground_truth_leaf_count","line_item_count","text_token_count","ocr_box_count","target-derived errors"]})
    clean=[r for r in docs if r["model"]=="Donut" and r["split"]=="validation"]
    blur=np.array([float(r["blur"]) for r in clean]); tokens=np.array([float(r["text_token_count"]) for r in clean])
    stress_score=(blur-blur.mean())/(blur.std() or 1)-(tokens-tokens.mean())/(tokens.std() or 1)
    shifted=[clean[i] for i in np.argsort(stress_score)[:50]]
    reference=clean[:50]
    metrics=[]
    for name in ["blur","contrast","estimated_skew","image_megapixels","text_token_count","line_item_count","aspect_ratio","confidence","risk_score","latency_seconds"]:
        a=np.array([1-float(r["confidence"]) if name=="risk_score" else float(r[name]) for r in reference]); b=np.array([1-float(r["confidence"]) if name=="risk_score" else float(r[name]) for r in shifted]); pooled=np.concatenate([a,b]); bins=np.unique(np.quantile(pooled,np.linspace(0,1,11))); psi=0
        if len(bins)>1:
            for lo,hi in zip(bins[:-1],bins[1:]):
                pa=max(1e-6,float(((a>=lo)&(a<hi)).mean())); pb=max(1e-6,float(((b>=lo)&(b<hi)).mean())); psi+=(pb-pa)*math.log(pb/pa)
        metrics.append({"feature":name,"reference_mean":float(a.mean()),"current_mean":float(b.mean()),"standardized_mean_difference":float((b.mean()-a.mean())/(np.std(pooled) or 1)),"psi":psi,"alert":abs((b.mean()-a.mean())/(np.std(pooled) or 1))>=.5 or psi>=.2})
    write_csv(OUT/"drift/drift_metrics.csv",metrics)
    threshold=float(np.quantile([float(r["confidence"]) for r in clean],.2))
    ref_review=sum(float(r["confidence"])<=threshold for r in reference); cur_review=sum(float(r["confidence"])<=threshold for r in shifted)
    observed=np.array([[ref_review,len(reference)-ref_review],[cur_review,len(shifted)-cur_review]],float); expected=observed.sum(axis=1)[:,None]*observed.sum(axis=0)[None,:]/observed.sum(); chi2=float(np.sum((observed-expected)**2/np.where(expected,expected,1)))
    write_json(OUT/"drift/categorical_route_shift.json",{"route_policy":"REVIEW when raw confidence is at or below the development-derived 20% review threshold","threshold":threshold,"reference":{"REVIEW":ref_review,"AUTO":len(reference)-ref_review},"current":{"REVIEW":cur_review,"AUTO":len(shifted)-cur_review},"total_variation_distance":abs(ref_review/len(reference)-cur_review/len(shifted)),"pearson_chi_square_statistic":chi2,"descriptive_only":True})
    write_json(OUT/"drift/simulation_definition.json",{"label":"SIMULATED_STRESS_TEST_DRIFT","reference":"first 50 CORD validation documents in canonical order","current":"50 validation documents selected by equal-weight standardized lower-blur and higher-token-count stress score","prediction_output_descriptors":["confidence","risk_score=1-confidence","20% review route","latency"],"production_data":False,"interpretation":"Transparent image-quality and complexity stress simulation; not observed bank drift."})


def provenance() -> None:
    sources=["artifacts/v2/results/donut_development.json","artifacts/v2/results/final_donut.json","artifacts/v2/results/final_paddleocr.json","artifacts/v2/results/paddleocr_vl_development.json","artifacts/v3/serving/paddleocr_vllm_comparison.json","configs/v3_1/analysis_protocol.json","configs/v3_1/error_taxonomy.json"]
    write_json(OUT/"data/provenance.json",{"experiment_id":"V3.1-E01","derivation_script":"scripts/v3_1/build_analysis.py","sources":{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},"feature_provenance":{"ground_truth_and_structure":"authorized canonical CORD JSONL","image_quality":"OpenCV deterministic descriptors on authorized local images","predictions_and_latency":"committed frozen prediction artifacts","confidence":"model-emitted values only","unavailable_values":"empty; never imputed"}})


def main() -> None:
    docs,fields=build_tables(); provenance(); slicing(docs); errors(fields,docs); calibration_and_risk(docs); discovery_and_drift(docs)
    print(json.dumps({"documents":len(docs),"fields":len(fields),"output":str(OUT)},sort_keys=True))


if __name__ == "__main__": main()
