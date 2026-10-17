# Summary (seeds=30, budget=30, sigma=0.1)

Synthetic data only. VERIFIED-SYNTHETIC. Not evidence about LLMs.

| law | mechanism | recovered | exact terms | median test RMSE | expansions | null: any false term |
|---|---|---|---|---|---|---|
| in_space | M1_fixed_search | 27/30 | 30/30 | 0.0323 | 0/30 | - |
| in_space | M2_active_fixed_space | 29/30 | 30/30 | 0.0213 | 0/30 | - |
| in_space | M3_expand | 28/30 | 30/30 | 0.0196 | 0/30 | - |
| needs_expansion | M1_fixed_search | 0/30 | 0/30 | 0.3375 | 0/30 | - |
| needs_expansion | M2_active_fixed_space | 0/30 | 0/30 | 0.3472 | 0/30 | - |
| needs_expansion | M3_expand | 29/30 | 30/30 | 0.0259 | 30/30 | - |
| null | M1_fixed_search | 19/30 | 13/30 | 0.0407 | 0/30 | 17/30 |
| null | M2_active_fixed_space | 24/30 | 12/30 | 0.0283 | 0/30 | 18/30 |
| null | M3_expand | 27/30 | 11/30 | 0.0276 | 0/30 | 19/30 |
