# Step 7: threshold/override comparison (aggregate-only)

## fha_same-window

| threshold candidate | overrides | n_flagged | %flagged | recall | precision | auc | ks |
|---|---|---|---|---|---|---|---|
| current (0.025) | without | 24678 | 73.0010% | 89.0756% | 0.8591% | 0.6669 | 0.2778 |
| current (0.025) | with | 13969 | 41.3223% | 71.0084% | 1.2098% | 0.6669 | 0.2778 |
| best_threshold (0.2000) | without | 18502 | 54.7315% | 65.9664% | 0.8486% | 0.6669 | 0.2778 |
| best_threshold (0.2000) | with | 9477 | 28.0343% | 55.4622% | 1.3928% | 0.6669 | 0.2778 |
| target_15pct (0.0655) | without | 21819 | 64.5437% | 79.8319% | 0.8708% | 0.6669 | 0.2778 |
| target_15pct (0.0655) | with | 12305 | 36.3999% | 67.2269% | 1.3003% | 0.6669 | 0.2778 |

## fha_production-window

| threshold candidate | overrides | n_flagged | %flagged | recall | precision | auc | ks |
|---|---|---|---|---|---|---|---|
| current (0.025) | without | 24546 | 72.6106% | 91.5966% | 0.8881% | 0.7305 | 0.3637 |
| current (0.025) | with | 13573 | 40.1509% | 71.0084% | 1.2451% | 0.7305 | 0.3637 |
| best_threshold (0.1000) | without | 16911 | 50.0251% | 74.7899% | 1.0526% | 0.7305 | 0.3637 |
| best_threshold (0.1000) | with | 9157 | 27.0877% | 62.1849% | 1.6162% | 0.7305 | 0.3637 |
| target_15pct (0.0756) | without | 18895 | 55.8941% | 79.4118% | 1.0003% | 0.7305 | 0.3637 |
| target_15pct (0.0756) | with | 9810 | 29.0194% | 65.5462% | 1.5902% | 0.7305 | 0.3637 |

## conventional_same-window

| threshold candidate | overrides | n_flagged | %flagged | recall | precision | auc | ks |
|---|---|---|---|---|---|---|---|
| current (0.025) | without | 63989 | 89.6481% | 97.7578% | 0.3407% | 0.6567 | 0.2394 |
| current (0.025) | with | 22064 | 30.9115% | 64.1256% | 0.6481% | 0.6567 | 0.2394 |
| best_threshold (0.2000) | without | 26334 | 36.8937% | 59.6413% | 0.5051% | 0.6567 | 0.2394 |
| best_threshold (0.2000) | with | 18086 | 25.3383% | 53.8117% | 0.6635% | 0.6567 | 0.2394 |
| target_15pct (0.0833) | without | 44151 | 61.8552% | 81.6143% | 0.4122% | 0.6567 | 0.2394 |
| target_15pct (0.0833) | with | 20194 | 28.2916% | 60.5381% | 0.6685% | 0.6567 | 0.2394 |

## conventional_production-window

| threshold candidate | overrides | n_flagged | %flagged | recall | precision | auc | ks |
|---|---|---|---|---|---|---|---|
| current (0.025) | without | 64942 | 90.9832% | 98.6547% | 0.3388% | 0.6496 | 0.2350 |
| current (0.025) | with | 22454 | 31.4579% | 64.5740% | 0.6413% | 0.6496 | 0.2350 |
| best_threshold (0.1000) | without | 39859 | 55.8421% | 76.6816% | 0.4290% | 0.6496 | 0.2350 |
| best_threshold (0.1000) | with | 19450 | 27.2493% | 58.2960% | 0.6684% | 0.6496 | 0.2350 |
| target_15pct (0.0758) | without | 44309 | 62.0766% | 81.6143% | 0.4108% | 0.6496 | 0.2350 |
| target_15pct (0.0758) | with | 19991 | 28.0072% | 60.5381% | 0.6753% | 0.6496 | 0.2350 |
