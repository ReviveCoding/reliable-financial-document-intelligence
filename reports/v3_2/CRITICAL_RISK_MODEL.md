# Critical risk model

R4 shallow gradient boosting is the best learned candidate, selected strictly from development data. Its grouped-CV AURC is 0.2835, versus 0.2550 for R0: relative improvement -11.2% (negative means worse). The 95% document-bootstrap interval for absolute reduction is [-0.1674, 0.0992].

On retrospective CORD test, R0 AURC/PR-AUC/AUROC are 0.2356/0.8200/0.8189; R4 gives 0.3314/0.5754/0.6554. The retrospective R0−R4 AURC reduction is -0.0958, 95% CI [-0.2022, 0.0107].

Top nonzero production-safe R4 importances are `foreground_density` (0.345), `missing_discount` (0.314), `sequence_confidence` (0.232), `edge_density` (0.053), `predicted_long_description` (0.034). They describe the fitted model, not causal effects. The learned combination did not rank failures better than raw confidence.
