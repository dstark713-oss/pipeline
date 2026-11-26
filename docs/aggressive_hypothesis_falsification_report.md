# Aggressive Agent: Hypothesis Falsification Report

- Signal sample: **2005-01-11 to 2026-11-26**
- PIT TOP50 rows with current bars: **198,005**
- Securities: **205**
- Non-missing ticker/benchmark forward-RS observations across all horizons: **96.1%**
- Benchmark: daily rebalanced equal-weight PIT TOP50, with prior-session membership.
- Horizons: 3, 5, 10, and 20 global adjusted-market sessions.
- No ticker price forward-fill. A missing close at exact t+h produces a missing outcome.
- Daily date-level spreads retain the full cross-section before time-series inference; date-block resampling therefore preserves within-date cross-sectional dependence.
- No strategy return, BUY/SELL instruction, or position sizing is produced.

## Important identification note

- RS20 equals absolute return20 minus the same-date benchmark return20, and RS5 equals absolute return5 minus the same-date benchmark return5. Each pair is therefore perfectly collinear within a date. RS5 is the equivalent cross-sectional control for absolute return5; realized volatility20 is added as a separate non-collinear control.
- Therefore F1 tests RS20 incremental to RS5 and realized volatility20. It does not include absolute return5 beside RS5 or absolute return20 beside RS20, because those pairs are mathematically collinear within each date.

## F1: Does RS20 add information beyond RS5?

Two complementary tests: (a) within each RS5 quintile, compare top-quintile RS20 names with the remaining names in that same RS5 stratum; (b) date-wise cross-sectional regressions of forward RS on standardized RS20, RS5, and realized volatility20. The coefficient series is then tested through time.

## F2: Does 5D/20D alignment add information?

Report forward relative returns for all four sign quadrants and estimate a date-wise continuous interaction model: forward RS ~ standardized return5 + standardized return20 + their interaction. Alignment is not credited merely because the positive-both group beats the universe; its incremental interaction must also be considered.

## F3: Is persistent weakness more than a one-horizon effect?

Compare names weak on both RS5 and RS20 with RS5-only weak names, RS20-only weak names, and the remaining cross-section. Stability is reported by historical subperiod. A negative result is not automatically a short signal.

## F4: Do concentrated impulses underperform distributed impulses?

Within the positive 5D-return top quintile, split names by the within-date median of largest absolute daily log-return share. Compare forward RS, positive hit rate, and negative forward-RS frequency; separately regress forward RS on concentration and 5D return to test concentration beyond impulse magnitude.

## Primary contrast summaries

### F1 RS20 matched within RS5

| Contrast | Horizon | Mean spread | NW 95% CI | Block 95% CI | Dates | q |
|---|---:|---:|---:|---:|---:|---:|
| F1_H2_RS20_incremental_within_RS5 | 3 | 0.118% | [0.019%, 0.217%] | [0.026%, 0.216%] | 4,894 | 0.020 |
| F1_H2_RS20_incremental_within_RS5 | 5 | 0.238% | [0.085%, 0.392%] | [0.102%, 0.399%] | 4,879 | 0.004 |
| F1_H2_RS20_incremental_within_RS5 | 10 | 0.445% | [0.173%, 0.716%] | [0.177%, 0.720%] | 4,840 | 0.004 |
| F1_H2_RS20_incremental_within_RS5 | 20 | 0.693% | [0.232%, 1.154%] | [0.264%, 1.148%] | 4,768 | 0.004 |

### F3 persistent weakness

| Contrast | Horizon | Mean spread | NW 95% CI | Block 95% CI | Dates | q |
|---|---:|---:|---:|---:|---:|---:|
| vs_RS20_only | 3 | 0.100% | [-0.041%, 0.240%] | [-0.044%, 0.234%] | 3,378 | 0.327 |
| vs_RS20_only | 5 | 0.116% | [-0.074%, 0.305%] | [-0.064%, 0.293%] | 3,367 | 0.348 |
| vs_RS20_only | 10 | 0.263% | [-0.039%, 0.566%] | [-0.036%, 0.542%] | 3,345 | 0.212 |
| vs_RS20_only | 20 | -0.011% | [-0.434%, 0.412%] | [-0.441%, 0.374%] | 3,316 | 0.959 |
| vs_RS5_only | 3 | -0.004% | [-0.138%, 0.129%] | [-0.137%, 0.123%] | 3,386 | 0.959 |
| vs_RS5_only | 5 | -0.036% | [-0.234%, 0.161%] | [-0.232%, 0.154%] | 3,375 | 0.863 |
| vs_RS5_only | 10 | -0.138% | [-0.497%, 0.221%] | [-0.487%, 0.219%] | 3,351 | 0.602 |
| vs_RS5_only | 20 | -0.581% | [-1.170%, 0.009%] | [-1.177%, -0.033%] | 3,317 | 0.195 |
| vs_other | 3 | -0.093% | [-0.239%, 0.054%] | [-0.241%, 0.050%] | 3,650 | 0.348 |
| vs_other | 5 | -0.207% | [-0.427%, 0.013%] | [-0.430%, 0.008%] | 3,637 | 0.195 |
| vs_other | 10 | -0.413% | [-0.804%, -0.022%] | [-0.797%, -0.016%] | 3,612 | 0.195 |
| vs_other | 20 | -0.922% | [-1.574%, -0.269%] | [-1.525%, -0.308%] | 3,573 | 0.068 |

### F4 impulse concentration

| Contrast | Horizon | Mean spread | NW 95% CI | Block 95% CI | Dates | q |
|---|---:|---:|---:|---:|---:|---:|
| F4_H1_concentrated_minus_distributed | 3 | 0.073% | [-0.055%, 0.201%] | [-0.049%, 0.200%] | 3,786 | 0.527 |
| F4_H1_concentrated_minus_distributed | 5 | 0.138% | [-0.035%, 0.311%] | [-0.031%, 0.308%] | 3,775 | 0.472 |
| F4_H1_concentrated_minus_distributed | 10 | -0.008% | [-0.218%, 0.202%] | [-0.211%, 0.198%] | 3,744 | 0.940 |
| F4_H1_concentrated_minus_distributed | 20 | -0.086% | [-0.396%, 0.223%] | [-0.399%, 0.222%] | 3,693 | 0.780 |

## F1 conditional regression coefficients

| Horizon | Coefficient | Mean | NW 95% CI | Dates | q |
|---:|---|---:|---:|---:|---:|
| 3 | beta_rs20 | 0.00060 | [-0.00011, 0.00132] | 4,427 | 0.196 |
| 3 | beta_rs5 | -0.00010 | [-0.00072, 0.00053] | 4,427 | 0.855 |
| 3 | beta_vol20 | -0.00002 | [-0.00069, 0.00064] | 4,427 | 0.948 |
| 5 | beta_rs20 | 0.00119 | [0.00010, 0.00227] | 4,410 | 0.128 |
| 5 | beta_rs5 | -0.00012 | [-0.00093, 0.00068] | 4,410 | 0.855 |
| 5 | beta_vol20 | -0.00014 | [-0.00115, 0.00087] | 4,410 | 0.855 |
| 10 | beta_rs20 | 0.00270 | [0.00091, 0.00448] | 4,367 | 0.018 |
| 10 | beta_rs5 | -0.00101 | [-0.00207, 0.00006] | 4,367 | 0.154 |
| 10 | beta_vol20 | -0.00080 | [-0.00262, 0.00101] | 4,367 | 0.580 |
| 20 | beta_rs20 | 0.00532 | [0.00241, 0.00824] | 4,283 | 0.004 |
| 20 | beta_rs5 | -0.00153 | [-0.00302, -0.00004] | 4,283 | 0.135 |
| 20 | beta_vol20 | -0.00177 | [-0.00465, 0.00111] | 4,283 | 0.390 |

## F2 momentum quadrants

| Horizon | Quadrant | Mean forward RS | NW 95% CI | Dates | q |
|---:|---|---:|---:|---:|---:|
| 3 | negative_both | -0.179% | [-0.266%, -0.091%] | 5,485 | 0.000 |
| 3 | positive_20_only | -0.006% | [-0.086%, 0.073%] | 5,485 | 0.877 |
| 3 | positive_5_only | -0.060% | [-0.148%, 0.028%] | 5,485 | 0.208 |
| 3 | positive_both | 0.135% | [0.058%, 0.212%] | 5,485 | 0.002 |
| 5 | negative_both | -0.291% | [-0.425%, -0.157%] | 5,485 | 0.000 |
| 5 | positive_20_only | 0.050% | [-0.071%, 0.171%] | 5,485 | 0.443 |
| 5 | positive_5_only | -0.102% | [-0.230%, 0.027%] | 5,485 | 0.148 |
| 5 | positive_both | 0.188% | [0.080%, 0.296%] | 5,485 | 0.002 |
| 10 | negative_both | -0.449% | [-0.702%, -0.196%] | 5,485 | 0.002 |
| 10 | positive_20_only | 0.219% | [0.024%, 0.414%] | 5,485 | 0.040 |
| 10 | positive_5_only | -0.252% | [-0.442%, -0.062%] | 5,485 | 0.015 |
| 10 | positive_both | 0.192% | [0.014%, 0.371%] | 5,485 | 0.047 |
| 20 | negative_both | -0.806% | [-1.194%, -0.417%] | 5,485 | 0.000 |
| 20 | positive_20_only | 0.468% | [0.170%, 0.765%] | 5,485 | 0.004 |
| 20 | positive_5_only | -0.426% | [-0.709%, -0.144%] | 5,485 | 0.005 |
| 20 | positive_both | 0.429% | [0.162%, 0.696%] | 5,485 | 0.004 |

## F2 continuous interaction

| Horizon | Coefficient | Mean | NW 95% CI | Dates | q |
|---:|---|---:|---:|---:|---:|
| 3 | beta_return5 | 0.00015 | [-0.00038, 0.00068] | 4,499 | 0.757 |
| 3 | beta_return20 | 0.00073 | [0.00002, 0.00145] | 4,499 | 0.136 |
| 3 | beta_interaction | 0.00030 | [-0.00008, 0.00069] | 4,499 | 0.284 |
| 5 | beta_return5 | 0.00026 | [-0.00045, 0.00097] | 4,479 | 0.757 |
| 5 | beta_return20 | 0.00137 | [0.00038, 0.00235] | 4,479 | 0.026 |
| 5 | beta_interaction | 0.00007 | [-0.00045, 0.00058] | 4,479 | 0.864 |
| 10 | beta_return5 | -0.00009 | [-0.00116, 0.00098] | 4,431 | 0.868 |
| 10 | beta_return20 | 0.00274 | [0.00103, 0.00445] | 4,431 | 0.010 |
| 10 | beta_interaction | -0.00017 | [-0.00095, 0.00060] | 4,431 | 0.794 |
| 20 | beta_return5 | -0.00047 | [-0.00208, 0.00114] | 4,345 | 0.757 |
| 20 | beta_return20 | 0.00514 | [0.00226, 0.00802] | 4,345 | 0.006 |
| 20 | beta_interaction | -0.00071 | [-0.00189, 0.00046] | 4,345 | 0.470 |

## F4 concentration conditional on impulse size

| Horizon | Coefficient | Mean | NW 95% CI | Dates | q |
|---:|---|---:|---:|---:|---:|
| 3 | beta_concentration | 0.00007 | [-0.00070, 0.00084] | 2,827 | 0.979 |
| 3 | beta_return5 | 0.00161 | [0.00017, 0.00305] | 2,827 | 0.225 |
| 5 | beta_concentration | 0.00013 | [-0.00093, 0.00119] | 2,822 | 0.979 |
| 5 | beta_return5 | 0.00173 | [-0.00014, 0.00361] | 2,822 | 0.225 |
| 10 | beta_concentration | -0.00002 | [-0.00140, 0.00136] | 2,812 | 0.979 |
| 10 | beta_return5 | 0.00089 | [-0.00131, 0.00308] | 2,812 | 0.684 |
| 20 | beta_concentration | -0.00085 | [-0.00295, 0.00124] | 2,786 | 0.684 |
| 20 | beta_return5 | 0.00279 | [-0.00038, 0.00596] | 2,786 | 0.225 |

## F3 persistent weakness outside predefined crisis windows

Crisis windows excluded in this diagnostic: 2008-09-15 to 2009-06-30, 2020-02-20 to 2020-06-30, and 2022-02-24 to 2022-12-30. These exclusions are a robustness view only; the full-sample results remain primary.

### F3 crisis-excluded robustness

| Contrast | Horizon | Mean spread | NW 95% CI | Dates | q |
|---|---:|---:|---:|---:|---:|
| vs_RS20_only | 3 | 0.077% | [-0.067%, 0.221%] | 3,128 | 0.400 |
| vs_RS20_only | 5 | 0.103% | [-0.085%, 0.291%] | 3,117 | 0.400 |
| vs_RS20_only | 10 | 0.263% | [-0.045%, 0.571%] | 3,095 | 0.226 |
| vs_RS20_only | 20 | -0.081% | [-0.515%, 0.353%] | 3,066 | 0.715 |
| vs_RS5_only | 3 | -0.036% | [-0.174%, 0.102%] | 3,137 | 0.665 |
| vs_RS5_only | 5 | -0.083% | [-0.283%, 0.118%] | 3,126 | 0.501 |
| vs_RS5_only | 10 | -0.196% | [-0.568%, 0.175%] | 3,102 | 0.400 |
| vs_RS5_only | 20 | -0.668% | [-1.275%, -0.061%] | 3,068 | 0.117 |
| vs_other | 3 | -0.113% | [-0.264%, 0.038%] | 3,392 | 0.286 |
| vs_other | 5 | -0.237% | [-0.462%, -0.012%] | 3,378 | 0.117 |
| vs_other | 10 | -0.442% | [-0.848%, -0.036%] | 3,353 | 0.117 |
| vs_other | 20 | -0.977% | [-1.649%, -0.305%] | 3,317 | 0.053 |

## Stability by historical period

| Module | Horizon | Period | Mean effect | NW 95% CI | Dates |
|---|---:|---|---:|---:|---:|
| F1 | 3 | 2013_2019 | 0.00163 | [0.00012, 0.00314] | 1,757 |
| F1 | 3 | 2020_plus | 0.00121 | [-0.00027, 0.00269] | 1,683 |
| F1 | 3 | through_2012 | 0.00059 | [-0.00160, 0.00277] | 1,454 |
| F1 | 5 | 2013_2019 | 0.00328 | [0.00091, 0.00566] | 1,757 |
| F1 | 5 | 2020_plus | 0.00176 | [-0.00063, 0.00415] | 1,677 |
| F1 | 5 | through_2012 | 0.00201 | [-0.00126, 0.00528] | 1,445 |
| F1 | 10 | 2013_2019 | 0.00669 | [0.00265, 0.01073] | 1,757 |
| F1 | 10 | 2020_plus | 0.00301 | [-0.00143, 0.00744] | 1,662 |
| F1 | 10 | through_2012 | 0.00335 | [-0.00242, 0.00912] | 1,421 |
| F1 | 20 | 2013_2019 | 0.01289 | [0.00672, 0.01906] | 1,757 |
| F1 | 20 | 2020_plus | 0.00412 | [-0.00360, 0.01185] | 1,640 |
| F1 | 20 | through_2012 | 0.00264 | [-0.00764, 0.01292] | 1,371 |
| F3 | 3 | 2013_2019 | 0.00240 | [0.00032, 0.00447] | 1,539 |
| F3 | 3 | 2020_plus | -0.00016 | [-0.00217, 0.00184] | 1,604 |
| F3 | 3 | through_2012 | -0.00023 | [-0.00542, 0.00495] | 235 |
| F3 | 5 | 2013_2019 | 0.00359 | [0.00094, 0.00625] | 1,538 |
| F3 | 5 | 2020_plus | -0.00069 | [-0.00349, 0.00211] | 1,596 |
| F3 | 5 | through_2012 | -0.00230 | [-0.00902, 0.00442] | 233 |
| F3 | 10 | 2013_2019 | 0.00477 | [0.00024, 0.00929] | 1,535 |
| F3 | 10 | 2020_plus | 0.00050 | [-0.00379, 0.00480] | 1,581 |
| F3 | 10 | through_2012 | 0.00304 | [-0.00860, 0.01468] | 229 |
| F3 | 20 | 2013_2019 | 0.00400 | [-0.00220, 0.01020] | 1,536 |
| F3 | 20 | 2020_plus | -0.00429 | [-0.01041, 0.00183] | 1,559 |
| F3 | 20 | through_2012 | 0.00075 | [-0.01345, 0.01496] | 221 |
| F3 | 3 | 2013_2019 | -0.00007 | [-0.00218, 0.00204] | 1,543 |
| F3 | 3 | 2020_plus | -0.00037 | [-0.00217, 0.00142] | 1,605 |
| F3 | 3 | through_2012 | 0.00236 | [-0.00356, 0.00827] | 238 |
| F3 | 5 | 2013_2019 | -0.00005 | [-0.00306, 0.00297] | 1,542 |
| F3 | 5 | 2020_plus | -0.00139 | [-0.00419, 0.00142] | 1,597 |
| F3 | 5 | through_2012 | 0.00449 | [-0.00207, 0.01105] | 236 |
| F3 | 10 | 2013_2019 | -0.00186 | [-0.00706, 0.00335] | 1,537 |
| F3 | 10 | 2020_plus | -0.00237 | [-0.00769, 0.00294] | 1,582 |
| F3 | 10 | through_2012 | 0.00859 | [-0.00434, 0.02152] | 232 |
| F3 | 20 | 2013_2019 | -0.00345 | [-0.01120, 0.00429] | 1,534 |
| F3 | 20 | 2020_plus | -0.00943 | [-0.01867, -0.00020] | 1,560 |
| F3 | 20 | through_2012 | 0.00337 | [-0.02235, 0.02908] | 223 |
| F3 | 3 | 2013_2019 | 0.00048 | [-0.00175, 0.00271] | 1,599 |
| F3 | 3 | 2020_plus | -0.00289 | [-0.00490, -0.00087] | 1,615 |
| F3 | 3 | through_2012 | 0.00119 | [-0.00397, 0.00635] | 436 |
| F3 | 5 | 2013_2019 | 0.00030 | [-0.00303, 0.00363] | 1,598 |
| F3 | 5 | 2020_plus | -0.00481 | [-0.00783, -0.00178] | 1,607 |
| F3 | 5 | through_2012 | -0.00065 | [-0.00837, 0.00707] | 432 |
| F3 | 10 | 2013_2019 | -0.00126 | [-0.00707, 0.00456] | 1,595 |
| F3 | 10 | 2020_plus | -0.00696 | [-0.01259, -0.00132] | 1,592 |
| F3 | 10 | through_2012 | -0.00430 | [-0.01838, 0.00979] | 425 |
| F3 | 20 | 2013_2019 | -0.00450 | [-0.01357, 0.00457] | 1,594 |
| F3 | 20 | 2020_plus | -0.01454 | [-0.02422, -0.00487] | 1,570 |
| F3 | 20 | through_2012 | -0.00715 | [-0.03498, 0.02068] | 409 |
| F4 | 3 | 2013_2019 | 0.00133 | [-0.00078, 0.00345] | 1,707 |
| F4 | 3 | 2020_plus | 0.00094 | [-0.00087, 0.00274] | 1,570 |
| F4 | 3 | through_2012 | -0.00193 | [-0.00469, 0.00082] | 509 |
| F4 | 5 | 2013_2019 | 0.00182 | [-0.00098, 0.00461] | 1,703 |
| F4 | 5 | 2020_plus | 0.00231 | [-0.00023, 0.00486] | 1,566 |
| F4 | 5 | through_2012 | -0.00296 | [-0.00651, 0.00058] | 506 |
| F4 | 10 | 2013_2019 | 0.00007 | [-0.00302, 0.00316] | 1,701 |
| F4 | 10 | 2020_plus | 0.00209 | [-0.00124, 0.00543] | 1,553 |
| F4 | 10 | through_2012 | -0.00749 | [-0.01206, -0.00293] | 490 |
| F4 | 20 | 2013_2019 | -0.00065 | [-0.00558, 0.00428] | 1,698 |
| F4 | 20 | 2020_plus | 0.00044 | [-0.00407, 0.00496] | 1,524 |
| F4 | 20 | through_2012 | -0.00587 | [-0.01334, 0.00160] | 471 |
| F2_interaction | 3 | 2013_2019 | 0.00015 | [-0.00037, 0.00066] | 1,760 |
| F2_interaction | 3 | 2020_plus | 0.00017 | [-0.00028, 0.00062] | 1,687 |
| F2_interaction | 3 | through_2012 | 0.00078 | [-0.00040, 0.00196] | 1,052 |
| F2_interaction | 5 | 2013_2019 | -0.00011 | [-0.00080, 0.00058] | 1,760 |
| F2_interaction | 5 | 2020_plus | -0.00015 | [-0.00071, 0.00041] | 1,681 |
| F2_interaction | 5 | through_2012 | 0.00073 | [-0.00092, 0.00238] | 1,038 |
| F2_interaction | 10 | 2013_2019 | -0.00047 | [-0.00148, 0.00053] | 1,760 |
| F2_interaction | 10 | 2020_plus | -0.00043 | [-0.00140, 0.00054] | 1,666 |
| F2_interaction | 10 | through_2012 | 0.00078 | [-0.00166, 0.00322] | 1,005 |
| F2_interaction | 20 | 2013_2019 | 0.00030 | [-0.00115, 0.00175] | 1,760 |
| F2_interaction | 20 | 2020_plus | -0.00191 | [-0.00341, -0.00041] | 1,644 |
| F2_interaction | 20 | through_2012 | -0.00052 | [-0.00441, 0.00338] | 941 |

## Inference and limitations

- HAC Newey-West intervals and circular moving-block bootstrap are applied to daily date-level estimates. This preserves contemporaneous cross-sectional dependence because the resampling unit is the date-level statistic, not individual ticker rows.
- The bootstrap uses 20-session circular blocks for all reported contrast series; this is a common dependence-aware robustness check, not an exact finite-sample test.
- Forward horizons overlap. NW lag is conservatively set to 19 sessions for the reported date-level series.
- BH q-values are screening adjustments within each summary table. Effect size, interval, sample size, period stability, and economic plausibility matter more than a threshold alone.
- The subperiod split is descriptive and fixed: through 2012, 2013-2019, and 2020 onward.
- The 4 modules are falsification diagnostics, not optimized trading rules. Any surviving effect must still pass out-of-sample and implementation checks before a name-level signal is considered.

## Outputs

Markdown report: docs/aggressive_hypothesis_falsification_report.md
CSV files: data/interim/aggressive_hypothesis_falsification/
