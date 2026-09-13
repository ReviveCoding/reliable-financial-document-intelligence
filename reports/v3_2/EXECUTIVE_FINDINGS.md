# Executive findings

R-FDI v3.2 improves the *measurement* of receipt line items but does not produce a promotable risk controller. Permutation-invariant E2 test F1 is 0.9534, yet only 60.2% of rows are exact and critical monetary errors affect 41.0% of retrospective test documents.

Raw confidence remains the strongest evaluated ranker (AURC 0.2356, PR-AUC 0.8200, AUROC 0.8189). Learned R4 is worse (AURC 0.3314) and no 5/10/20% target is certified. The correct action is `V3_2_RISK_MODEL_NO_PROMOTION`: preserve the candidate offline, keep runtime semantics unchanged, and collect larger, genuinely external line-item evidence before another promotion attempt.

The clearest next fixes are line-item association, wrong item prices despite a correct total, and risk features sensitive to extraction degradation rather than appearance alone.
