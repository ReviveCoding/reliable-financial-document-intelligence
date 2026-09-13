# Corrected critical-risk model replay

R4 shallow gradient boosting remains the best learned candidate; R0 remains best overall. Development grouped-CV AURC is 0.2835 for R4 versus 0.2550 for R0, a -11.2% relative reduction (negative is worse), with absolute-reduction 95% CI [-0.1674, 0.0992].

Retrospective R0 AURC/PR-AUC/AUROC are 0.2356/0.8200/0.8189; R4 is 0.3314/0.5754/0.6554. Retrospective absolute R0−R4 AURC reduction is -0.0958, 95% CI [-0.2022, 0.0107]. Top fitted production-safe features are foreground_density, missing_discount, sequence_confidence, edge_density, predicted_long_description; importances are descriptive, not causal.
