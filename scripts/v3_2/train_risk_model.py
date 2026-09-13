from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any, Callable

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT=Path(__file__).resolve().parents[2]
PROTOCOL=json.loads((ROOT/"configs/v3_2/risk_protocol.json").read_text())
ERRATUM=json.loads((ROOT/"configs/v3_2/methodology_erratum.json").read_text())
SEED=int(PROTOCOL["determinism"]["seed"]); REPS=int(PROTOCOL["determinism"]["bootstrap_replicates"])


def boolean(value: str) -> float: return float(value.casefold()=="true")


def load(path: Path) -> tuple[list[dict[str,str]],list[str]]:
    rows=list(csv.DictReader(path.open())); dictionary=list(csv.DictReader((path.parent/"risk_feature_dictionary.csv").open()))
    features=[r["feature"] for r in dictionary if r["eligible_for_risk_model"]=="True"]
    return rows,features


def matrix(rows: list[dict[str,str]], features: list[str]) -> np.ndarray:
    values=[]
    for row in rows:
        current=[]
        for feature in features:
            value=row[feature]
            if value.casefold() in {"true","false"}: current.append(boolean(value))
            else:
                try: current.append(float(value))
                except ValueError: current.append(np.nan)
        values.append(current)
    data=np.asarray(values,float); medians=np.nanmedian(data,axis=0); medians=np.where(np.isnan(medians),0,medians)
    return np.where(np.isnan(data),medians,data)


def aurc(y: np.ndarray, score: np.ndarray) -> float:
    order=np.argsort(score,kind="stable"); cumulative=np.cumsum(y[order])/np.arange(1,len(y)+1); return float(cumulative.mean())


def ece(y: np.ndarray, score: np.ndarray, bins: int=10) -> float:
    total=0.0
    for low in np.linspace(0,1,bins,endpoint=False):
        use=(score>=low)&(score<(low+1/bins) if low+1/bins<1 else score<=1)
        if use.any(): total+=float(use.mean())*abs(float(score[use].mean()-y[use].mean()))
    return total


def metrics(y: np.ndarray, score: np.ndarray) -> dict[str,float]:
    return {"AURC":aurc(y,score),"PR_AUC":float(average_precision_score(y,score)),"AUROC":float(roc_auc_score(y,score)),"Brier":float(brier_score_loss(y,np.clip(score,0,1))),"ECE":ece(y,np.clip(score,0,1))}


def budgets(y: np.ndarray, score: np.ndarray) -> list[dict[str,float]]:
    order=np.argsort(-score,kind="stable"); total=float(y.sum()); output=[]
    for budget in PROTOCOL["review_budgets"]:
        n=round(len(y)*float(budget)); review=set(order[:n]); auto=[i for i in range(len(y)) if i not in review]
        output.append({"review_budget":float(budget),"automation_coverage":len(auto)/len(y),"critical_error_capture":float(y[list(review)].sum()/total) if total else 1.0,"critical_false_accept":float(y[auto].mean()) if auto else 0.0,"document_selective_risk":float(y[auto].mean()) if auto else 0.0})
    return output


def rank01(values: np.ndarray) -> np.ndarray:
    order=np.argsort(values,kind="stable"); ranks=np.empty(len(values),float); ranks[order]=np.arange(len(values)); return ranks/max(1,len(values)-1)


def oof_learned(x: np.ndarray,y: np.ndarray,groups: np.ndarray,kind: str,params: dict[str,Any]) -> np.ndarray:
    result=np.zeros(len(y)); folds=GroupKFold(n_splits=5)
    for train,valid in folds.split(x,y,groups):
        if kind=="R3": model=make_pipeline(StandardScaler(),LogisticRegression(C=params["C"],class_weight=params["class_weight"],max_iter=2000,random_state=SEED))
        else: model=GradientBoostingClassifier(n_estimators=params["n_estimators"],learning_rate=params["learning_rate"],max_depth=params["max_depth"],random_state=SEED)
        model.fit(x[train],y[train]); result[valid]=model.predict_proba(x[valid])[:,1]
    return result


def baseline_scores(rows: list[dict[str,str]], y: np.ndarray) -> dict[str,np.ndarray]:
    confidence=np.array([float(r["sequence_confidence"]) for r in rows]); conflict=np.array([float(r["reconciliation_contradiction_count"]) for r in rows])
    r0=1-confidence; r1=np.clip(r0+.3*conflict,0,1)
    result={"R0":r0,"R1":r1}; iso=np.zeros(len(rows)); groups=np.array([r["source_document_id"] for r in rows]); folds=GroupKFold(n_splits=5)
    for train,valid in folds.split(confidence,y,groups):
        model=IsotonicRegression(increasing=False,out_of_bounds="clip").fit(confidence[train],y[train]); iso[valid]=model.predict(confidence[valid])
    result["R2"]=iso; return result


def fit_model(kind: str,params: dict[str,Any],x: np.ndarray,y: np.ndarray):
    if kind=="R3": model=make_pipeline(StandardScaler(),LogisticRegression(C=params["C"],class_weight=params["class_weight"],max_iter=2000,random_state=SEED))
    else: model=GradientBoostingClassifier(n_estimators=params["n_estimators"],learning_rate=params["learning_rate"],max_depth=params["max_depth"],random_state=SEED)
    return model.fit(x,y)


def score_selected(bundle: dict[str,Any],x: np.ndarray,rows: list[dict[str,str]]) -> np.ndarray:
    kind=bundle["selected_candidate"]
    if kind=="R0": return 1-np.array([float(r["sequence_confidence"]) for r in rows])
    if kind=="R1": return np.clip(1-np.array([float(r["sequence_confidence"]) for r in rows])+.3*np.array([float(r["reconciliation_contradiction_count"]) for r in rows]),0,1)
    if kind=="R2": return bundle["model"].predict(np.array([float(r["sequence_confidence"]) for r in rows]))
    if kind in {"R3","R4"}: return bundle["model"].predict_proba(x)[:,1]
    return (rank01(bundle["R3_model"].predict_proba(x)[:,1])+rank01(bundle["R4_model"].predict_proba(x)[:,1]))/2


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--input",type=Path,required=True); parser.add_argument("--output-dir",type=Path,required=True); args=parser.parse_args()
    all_rows,features=load(args.input); fit=[r for r in all_rows if r["development_partition"]=="FIT"]; selection=[r for r in all_rows if r["development_partition"]=="THRESHOLD_SELECTION"]
    assert len(fit)==60 and len(selection)==20
    assert all(r["designation"]=="DEVELOPMENT_CORRECTION_REPLAY" for r in fit)
    assert all(r["designation"]=="DEVELOPMENT_THRESHOLD_REPLAY" for r in selection)
    x=matrix(fit,features); y=np.array([boolean(r["document_has_critical_error"]) for r in fit]); groups=np.array([r["source_document_id"] for r in fit]); candidate_scores=baseline_scores(fit,y); params_by_candidate: dict[str,dict[str,Any]]={}
    r3_grid=[{"C":c,"class_weight":w} for c,w in itertools.product([.1,1.0,10.0],[None,"balanced"])]
    r4_grid=[{"n_estimators":n,"learning_rate":lr,"max_depth":d} for n,lr,d in itertools.product([50,100],[.05,.1],[1,2])]
    for kind,grid in (("R3",r3_grid),("R4",r4_grid)):
        trials=[]
        for params in grid:
            score=oof_learned(x,y,groups,kind,params); trials.append((aurc(y,score),json.dumps(params,sort_keys=True),params,score))
        _,_,params,score=min(trials,key=lambda z:(z[0],z[1])); params_by_candidate[kind]=params; candidate_scores[kind]=score
    candidate_scores["R5"]=(rank01(candidate_scores["R3"])+rank01(candidate_scores["R4"]))/2
    table=[]
    for name,score in candidate_scores.items(): table.append({"candidate":name,**metrics(y,score)})
    learned_rows=[r for r in table if r["candidate"] in {"R3","R4","R5"}]
    best_learned=min(learned_rows,key=lambda r:r["AURC"]); logistic=next(r for r in table if r["candidate"]=="R3")
    selected="R3" if logistic["AURC"]<=best_learned["AURC"]*1.05 else str(best_learned["candidate"])
    selected_row=next(r for r in table if r["candidate"]==selected); baseline=next(r for r in table if r["candidate"]=="R0"); relative=(baseline["AURC"]-selected_row["AURC"])/baseline["AURC"] if baseline["AURC"] else 0
    rng=np.random.default_rng(SEED); absolute_deltas=[]; relative_deltas=[]
    for _ in range(REPS):
        take=rng.integers(0,len(y),len(y)); base_boot=aurc(y[take],candidate_scores["R0"][take]); learned_boot=aurc(y[take],candidate_scores[selected][take]); absolute_deltas.append(base_boot-learned_boot); relative_deltas.append((base_boot-learned_boot)/base_boot if base_boot else 0.0)
    budget_by={name:budgets(y,score) for name,score in candidate_scores.items()}; practical=False; operating=False
    for learned,raw in zip(budget_by[selected],budget_by["R0"]):
        if learned["review_budget"]<=.5:
            practical |= learned["critical_error_capture"]-raw["critical_error_capture"]>=.05 or raw["critical_false_accept"]-learned["critical_false_accept"]>=.05
            operating |= learned["critical_error_capture"]>=.85 or (learned["critical_false_accept"]<=.10 and learned["automation_coverage"]>=.5)
    bundle: dict[str,Any]={"selected_candidate":selected,"features":features,"parameters":params_by_candidate}
    if selected in {"R3","R4"}: bundle["model"]=fit_model(selected,params_by_candidate[selected],x,y)
    elif selected=="R2": bundle["model"]=IsotonicRegression(increasing=False,out_of_bounds="clip").fit(np.array([float(r["sequence_confidence"]) for r in fit]),y)
    elif selected=="R5": bundle["R3_model"]=fit_model("R3",params_by_candidate["R3"],x,y); bundle["R4_model"]=fit_model("R4",params_by_candidate["R4"],x,y)
    xs=matrix(selection,features); ys=np.array([boolean(r["document_has_critical_error"]) for r in selection]); raw_selection=score_selected(bundle,xs,selection)
    platt=LogisticRegression(C=1.0,max_iter=2000,random_state=SEED).fit(raw_selection.reshape(-1,1),ys); isotonic=IsotonicRegression(out_of_bounds="clip").fit(raw_selection,ys)
    thresholds=[]
    for target in PROTOCOL["certification"]["targets"]:
        candidates=[]
        for threshold in sorted(set(raw_selection)):
            accepted=ys[raw_selection<=threshold]
            if len(accepted)>=10 and float(accepted.mean())<=float(target): candidates.append((len(accepted),float(threshold),float(accepted.mean())))
        if candidates:
            accepted,threshold,observed=max(candidates); thresholds.append({"target_risk":target,"threshold":threshold,"selection_accepted_n":accepted,"selection_coverage":accepted/len(ys),"selection_observed_risk":observed})
        else: thresholds.append({"target_risk":target,"threshold":None,"selection_accepted_n":0,"selection_coverage":0,"selection_observed_risk":None})
    args.output_dir.mkdir(parents=True,exist_ok=True); joblib.dump({**bundle,"platt":platt,"isotonic":isotonic},args.output_dir/"selected_risk_model.joblib")
    with (args.output_dir/"candidate_grouped_cv_metrics.csv").open("w",newline="") as h: writer=csv.DictWriter(h,fieldnames=list(table[0]),lineterminator="\n"); writer.writeheader(); writer.writerows(sorted(table,key=lambda r:r["AURC"]))
    budget_rows=[{"candidate":name,**row} for name,values in budget_by.items() for row in values]
    with (args.output_dir/"grouped_cv_review_budgets.csv").open("w",newline="") as h: writer=csv.DictWriter(h,fieldnames=list(budget_rows[0]),lineterminator="\n"); writer.writeheader(); writer.writerows(budget_rows)
    best_overall=min(table,key=lambda row:row["AURC"])["candidate"]
    selection_payload={
        "protocol_sha256":hashlib.sha256((ROOT/"configs/v3_2/risk_protocol.json").read_bytes()).hexdigest(),
        "methodology_erratum_sha256":hashlib.sha256((ROOT/"configs/v3_2/methodology_erratum.json").read_bytes()).hexdigest(),
        "replay_designation":"METHODOLOGY_CORRECTION_REPLAY",
        "fresh_confirmatory_evidence":False,
        "promotion_eligible":False,
        "selected_candidate":selected,
        "selected_model_role":"BEST_LEARNED_CANDIDATE_FOR_EVALUATION; not promoted unless every frozen gate passes",
        "best_overall_candidate":best_overall,
        "selection_rule":"Choose the minimum grouped-CV AURC among R3/R4/R5, preferring interpretable R3 when its AURC is within 5% relative of that learned candidate.",
        "fit_documents":len(fit),
        "threshold_selection_documents":len(selection),
        "certification_outcomes_evaluated":False,
        "retrospective_test_accessed":False,
        "candidate_parameters":params_by_candidate,
        "baseline_R0_AURC":baseline["AURC"],
        "selected_AURC":selected_row["AURC"],
        "relative_AURC_reduction":relative,
        "document_group_bootstrap":{
            "replicates":REPS,
            "support_groups":len(set(groups)),
            "absolute_AURC_reduction_ci95":[float(np.quantile(absolute_deltas,.025)),float(np.quantile(absolute_deltas,.975))],
            "relative_AURC_reduction_ci95":[float(np.quantile(relative_deltas,.025)),float(np.quantile(relative_deltas,.975))],
        },
        "practical_improvement_gate":practical,
        "operating_gate":operating,
        "internal_development_gates_pass":relative>=.10 and practical and operating,
        "provisional_promotion_gates_pass":False,
        "promotion_prohibition_reason":"Certification and retrospective partitions were observed before methodology correction; genuinely fresh external evidence is required.",
        "thresholds":thresholds,
        "calibration_selection_metrics":{
            "uncalibrated":metrics(ys,raw_selection),
            "platt":metrics(ys,platt.predict_proba(raw_selection.reshape(-1,1))[:,1]),
            "isotonic":metrics(ys,isotonic.predict(raw_selection)),
        },
        "features":features,
        "model_artifact_sha256":hashlib.sha256((args.output_dir/"selected_risk_model.joblib").read_bytes()).hexdigest(),
    }
    (args.output_dir/"frozen_selection.json").write_text(json.dumps(selection_payload,indent=2,sort_keys=True)+"\n")
    importance=[]
    if selected=="R3":
        coefs=bundle["model"].named_steps["logisticregression"].coef_[0]
        importance=[{"feature":f,"importance":abs(float(c)),"direction":"risk_increases" if c>0 else "risk_decreases"} for f,c in zip(features,coefs)]
    elif selected=="R4": importance=[{"feature":f,"importance":float(v),"direction":"nonlinear"} for f,v in zip(features,bundle["model"].feature_importances_)]
    else: importance=[{"feature":f,"importance":0.0,"direction":"baseline_or_ensemble"} for f in features]
    with (args.output_dir/"feature_importance.csv").open("w",newline="") as h: writer=csv.DictWriter(h,fieldnames=list(importance[0]),lineterminator="\n"); writer.writeheader(); writer.writerows(sorted(importance,key=lambda r:r["importance"],reverse=True))
    print(json.dumps(selection_payload,sort_keys=True))


if __name__=="__main__": main()
