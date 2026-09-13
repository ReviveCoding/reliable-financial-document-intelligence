from __future__ import annotations

import csv
import json
import subprocess
from io import StringIO
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OLD="10783326e4cb3e56b205df989e515f75ee3af997"


def current(path: str) -> list[dict[str,str]]:
    return list(csv.DictReader((ROOT/path).open()))


def historical(path: str) -> list[dict[str,str]]:
    text=subprocess.check_output(["git","show",f"{OLD}:{path}"],cwd=ROOT,text=True)
    return list(csv.DictReader(StringIO(text)))


paths={"validation":"artifacts/v3_2/data/development_risk_feature_table.csv","test":"artifacts/v3_2/data/retrospective_risk_feature_table.csv"}
output=[]
for split,path in paths.items():
    old={row["document_id"]:row for row in historical(path)}
    for row in current(path):
        before=old[row["document_id"]]; old_label=before["document_has_critical_error"].casefold()=="true"; new_label=row["document_has_critical_error"].casefold()=="true"
        old_loss=float(before["weighted_critical_loss"]); new_loss=float(row["weighted_critical_loss"])
        permutation=row["row_permutation_only"].casefold()=="true"; semantic=row["document_has_row_semantic_association_error"].casefold()=="true"
        if old_label and not new_label and permutation: reason="BENIGN_PERMUTATION_ONLY_REMOVED"
        elif old_label and not new_label: reason="ASSIGNMENT_ONLY_PENALTY_REMOVED"
        elif not old_label and new_label: reason="MONETARY_ASSOCIATION_ERROR_NOW_EXPLICIT"
        elif abs(old_loss-new_loss)>1e-15: reason="WEIGHTED_LOSS_RECOMPUTED_WITHOUT_ASSIGNMENT_ONLY_PENALTY_OR_WITH_EXPLICIT_ASSOCIATION"
        else: reason="UNCHANGED"
        output.append({"document_id":row["document_id"],"split":split,"old_critical_error_label":old_label,"corrected_critical_error_label":new_label,"old_weighted_loss":old_loss,"corrected_weighted_loss":new_loss,"row_permutation_only":permutation,"row_semantic_association_error":semantic,"reason_for_change":reason})
out=ROOT/"artifacts/v3_2/audit/label_transition.csv"
with out.open("w",newline="") as handle:
    writer=csv.DictWriter(handle,fieldnames=list(output[0]),lineterminator="\n"); writer.writeheader(); writer.writerows(output)
summary={
    "pre_correction_commit":OLD,"documents":len(output),"fresh_confirmatory_evidence":False,
    "unchanged_labels":sum(r["old_critical_error_label"]==r["corrected_critical_error_label"] for r in output),
    "positive_to_negative":sum(r["old_critical_error_label"] and not r["corrected_critical_error_label"] for r in output),
    "negative_to_positive":sum(not r["old_critical_error_label"] and r["corrected_critical_error_label"] for r in output),
    "weighted_loss_decreased":sum(r["corrected_weighted_loss"]<r["old_weighted_loss"]-1e-15 for r in output),
    "weighted_loss_increased":sum(r["corrected_weighted_loss"]>r["old_weighted_loss"]+1e-15 for r in output),
    "weighted_loss_unchanged":sum(abs(r["corrected_weighted_loss"]-r["old_weighted_loss"])<=1e-15 for r in output),
    "changes_attributable_solely_to_benign_permutation":sum(r["reason_for_change"]=="BENIGN_PERMUTATION_ONLY_REMOVED" for r in output),
    "permutation_only_documents":sum(r["row_permutation_only"] for r in output),
    "semantic_association_documents":sum(r["row_semantic_association_error"] for r in output),
}
(ROOT/"artifacts/v3_2/audit/label_transition_summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
print(json.dumps(summary,sort_keys=True))
