# Step 8: Final before/after comparison

Both sides: identical `evaluate.py` harness, identical June+July+August 2026 actuals.

## fha_same-window

| metric | before (original, 0.025+overrides) | after (fixed, best_threshold+overrides) | delta |
|---|---|---|---|
| recall | 71.43% | 55.46% | -0.1597 |
| precision | 1.2098% | 1.3928% | +0.0018 |
| pct_flagged | 41.57% | 28.03% | -0.1353 |
| legacy_specificity | 41.57% | 28.03% | -0.1353 |
| auc | 0.6764 | 0.6669 | -0.0095 |
| ks | 0.2902 | 0.2778 | -0.0124 |
| confusion matrix (TP/FP/FN/TN) | 170/13882/68/19685 | 132/9345/106/24222 | - |
| threshold used | 0.025 | 0.2000 | - |

## fha_production-window

| metric | before (original, 0.025+overrides) | after (fixed, best_threshold+overrides) | delta |
|---|---|---|---|
| recall | 70.59% | 62.18% | -0.0840 |
| precision | 1.2202% | 1.6162% | +0.0040 |
| pct_flagged | 40.73% | 27.09% | -0.1364 |
| legacy_specificity | 40.73% | 27.09% | -0.1364 |
| auc | 0.7344 | 0.7305 | -0.0039 |
| ks | 0.3496 | 0.3637 | +0.0142 |
| confusion matrix (TP/FP/FN/TN) | 168/13600/70/19967 | 148/9009/90/24558 | - |
| threshold used | 0.025 | 0.1000 | - |

## conventional_same-window

| metric | before (original, 0.025+overrides) | after (fixed, best_threshold+overrides) | delta |
|---|---|---|---|
| recall | 64.57% | 53.81% | -0.1076 |
| precision | 0.6438% | 0.6635% | +0.0002 |
| pct_flagged | 31.34% | 25.34% | -0.0600 |
| legacy_specificity | 31.34% | 25.34% | -0.0600 |
| auc | 0.6493 | 0.6567 | +0.0074 |
| ks | 0.2295 | 0.2394 | +0.0099 |
| confusion matrix (TP/FP/FN/TN) | 144/22223/79/48932 | 120/17966/103/53189 | - |
| threshold used | 0.025 | 0.2000 | - |

## conventional_production-window

| metric | before (original, 0.025+overrides) | after (fixed, best_threshold+overrides) | delta |
|---|---|---|---|
| recall | 64.13% | 58.30% | -0.0583 |
| precision | 0.6550% | 0.6684% | +0.0001 |
| pct_flagged | 30.59% | 27.25% | -0.0334 |
| legacy_specificity | 30.59% | 27.25% | -0.0334 |
| auc | 0.6294 | 0.6496 | +0.0202 |
| ks | 0.1963 | 0.2350 | +0.0386 |
| confusion matrix (TP/FP/FN/TN) | 143/21688/80/49467 | 130/19320/93/51835 | - |
| threshold used | 0.025 | 0.1000 | - |
