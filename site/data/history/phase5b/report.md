# Phase 5B tidal-aware forecasting and robustness validation

Research-only retrospective hindcasts in native MAUL1 gage height; not operational forecasts or flood probabilities.

Calibration is 2016–2022; holdout is 2023 onward and is a reused benchmark already inspected in Phase 5A. Features, alpha and the gate are fitted by blocked forward calibration validation with 72-hour target embargo. All forecast inputs use completed issue-time bins. The 4.0-ft NAVD88 threshold is not assessed.

## Holdout MAE and persistence-relative skill

Rows use each method's eligible paired issue times; differences against Phase 5A should use identical samples. Overlapping hourly forecasts are not independent.

| Horizon | Method | n | MAE (ft) | Skill vs persistence | Bias (ft) | 95% blocked MAE interval |
|---:|---|---:|---:|---:|---:|---|
| 6 h | persistence_ft | 32475 | 0.17423341031562742 | 0.0 | -3.0792917628945424e-05 | 0.16973411085450346–0.1783991570438799 |
| 6 h | maul1_only_ft | 32475 | 0.09335152397981779 | 0.46421571034677234 | 0.0019857937658174472 | 0.09034115378877472–0.09678728610523801 |
| 6 h | maul1_plus_coastal_ft | 32475 | 0.06306666077633286 | 0.6380334824297689 | 0.005390644871560756 | 0.06068072721621634–0.06541064887804797 |
| 6 h | maul1_plus_river_ft | 32475 | 0.09314439053140226 | 0.4654045377251741 | 0.0040890834485938716 | 0.09017742958119862–0.09661378441197307 |
| 6 h | maul1_periodic | 32475 | 0.09314474562817725 | 0.4654024996730327 | 0.0019606717979093816 | 0.08987398104814094–0.09650958534921972 |
| 6 h | maul1_coastal_tidal | 32475 | 0.06262061226856765 | 0.640593545433513 | 0.0010025949041930638 | 0.06028058035565068–0.06499813035057307 |
| 6 h | full_multivariable | 32475 | 0.06383015254251381 | 0.6336514769074187 | 0.013010253280031078 | 0.06151476244401313–0.06636727702766726 |
| 6 h | gated_full | 32475 | 0.09396903187455637 | 0.46067156864846115 | 0.0018578743088471365 | 0.0908908482395708–0.0972080895039957 |
| 12 h | persistence_ft | 32445 | 0.24151024811218988 | 0.0 | 0.00018893512097395573 | 0.23508883109878256–0.24754882493450453 |
| 12 h | maul1_only_ft | 32445 | 0.16294059741576988 | 0.3253263632105652 | 0.005084383896290393 | 0.15577160933889642–0.17013529096622726 |
| 12 h | maul1_plus_coastal_ft | 32445 | 0.1217673030300948 | 0.495808960564151 | 0.0008756140566802876 | 0.11664703305741336–0.1267355784101954 |
| 12 h | maul1_plus_river_ft | 32445 | 0.16213518980924047 | 0.3286612428391732 | 0.01037164243815079 | 0.154943195489971–0.16897435824825074 |
| 12 h | maul1_periodic | 32445 | 0.1626995145911321 | 0.32632459341620756 | 0.005055605668733993 | 0.15527654739164518–0.17010828206118947 |
| 12 h | maul1_coastal_tidal | 32445 | 0.1218623997174091 | 0.49541520217063506 | 0.006399069507661823 | 0.11677787748126414–0.12716803624914613 |
| 12 h | full_multivariable | 32445 | 0.12230992734645085 | 0.4935621643283905 | 0.013241852811562396 | 0.11717758989306352–0.1271763516895749 |
| 12 h | gated_full | 32445 | 0.16330013894086812 | 0.32383764160181916 | 0.0049257560894599315 | 0.15645181994275667–0.17042251630508748 |
| 24 h | persistence_ft | 32406 | 0.24025766833302473 | 0.0 | 0.00011355921742887229 | 0.22513117169659938–0.25641537061038083 |
| 24 h | maul1_only_ft | 32406 | 0.21543599321789614 | 0.10331272790312318 | 0.011535416302487557 | 0.203748194981358–0.228864702373796 |
| 24 h | maul1_plus_coastal_ft | 32406 | 0.1911400892442016 | 0.20443709218363237 | -0.017013142812020265 | 0.18145387513856368–0.20096190800693903 |
| 24 h | maul1_plus_river_ft | 32406 | 0.21593000721892958 | 0.10125654378853877 | 0.021970789464539384 | 0.2052495039886661–0.2280309335963072 |
| 24 h | maul1_periodic | 32406 | 0.21538850930251693 | 0.10351036536339098 | 0.011516442710626936 | 0.20316754208643248–0.22775842810732747 |
| 24 h | maul1_coastal_tidal | 32406 | 0.1901814226084282 | 0.20842725259110184 | 0.017200001375295707 | 0.18113004553754763–0.20016138869895392 |
| 24 h | full_multivariable | 32406 | 0.19113011543753627 | 0.2044786051423425 | 0.002227761483367434 | 0.18201431145438765–0.2006128790285408 |
| 24 h | gated_full | 32406 | 0.21562714453927528 | 0.10251711824493659 | 0.01148096263756529 | 0.20344615617507938–0.22761214682630504 |

## Paired model comparison on shared issue times

All methods below use the same eligible issue/target rows at each horizon; this is the preferred incremental comparison.

| Horizon | Paired n | Method | MAE (ft) | Skill vs persistence |
|---:|---:|---|---:|---:|
| 6 h | 32475 | persistence_ft | 0.17423341031562742 | 0.0 |
| 6 h | 32475 | maul1_only_ft | 0.09335152397981779 | 0.46421571034677234 |
| 6 h | 32475 | maul1_plus_river_ft | 0.09314439053140226 | 0.4654045377251741 |
| 6 h | 32475 | maul1_plus_coastal_ft | 0.06306666077633286 | 0.6380334824297689 |
| 6 h | 32475 | maul1_periodic | 0.09314474562817725 | 0.4654024996730327 |
| 6 h | 32475 | maul1_coastal_tidal | 0.06262061226856765 | 0.640593545433513 |
| 6 h | 32475 | full_multivariable | 0.06383015254251381 | 0.6336514769074187 |
| 6 h | 32475 | gated_full | 0.09396903187455637 | 0.46067156864846115 |
| 12 h | 32445 | persistence_ft | 0.24151024811218988 | 0.0 |
| 12 h | 32445 | maul1_only_ft | 0.16294059741576988 | 0.3253263632105652 |
| 12 h | 32445 | maul1_plus_river_ft | 0.16213518980924047 | 0.3286612428391732 |
| 12 h | 32445 | maul1_plus_coastal_ft | 0.1217673030300948 | 0.495808960564151 |
| 12 h | 32445 | maul1_periodic | 0.1626995145911321 | 0.32632459341620756 |
| 12 h | 32445 | maul1_coastal_tidal | 0.1218623997174091 | 0.49541520217063506 |
| 12 h | 32445 | full_multivariable | 0.12230992734645085 | 0.4935621643283905 |
| 12 h | 32445 | gated_full | 0.16330013894086812 | 0.32383764160181916 |
| 24 h | 32406 | persistence_ft | 0.24025766833302473 | 0.0 |
| 24 h | 32406 | maul1_only_ft | 0.21543599321789614 | 0.10331272790312318 |
| 24 h | 32406 | maul1_plus_river_ft | 0.21593000721892958 | 0.10125654378853877 |
| 24 h | 32406 | maul1_plus_coastal_ft | 0.1911400892442016 | 0.20443709218363237 |
| 24 h | 32406 | maul1_periodic | 0.21538850930251693 | 0.10351036536339098 |
| 24 h | 32406 | maul1_coastal_tidal | 0.1901814226084282 | 0.20842725259110184 |
| 24 h | 32406 | full_multivariable | 0.19113011543753627 | 0.2044786051423425 |
| 24 h | 32406 | gated_full | 0.21562714453927528 | 0.10251711824493659 |

This paired table answers whether tidal features, additional river/coastal evidence, or issue-time gating add value over the Phase 5A coastal reference on identical opportunities. Read it together with rising-water bias; overall MAE alone is insufficient.

## Interpretation of incremental changes

At 6 h, adding issue-time harmonics to MAUL1 changes MAE by -0.0002 ft versus Phase 5A MAUL1-only. The tidal/coastal candidate changes MAE by -0.0004 ft versus the Phase 5A coastal candidate; the full river/coastal candidate changes it by +0.0008 ft. The Phase 5A river-only comparator MAE is 0.0931 ft. The calibration-fitted gate changes paired MAE by +0.0309 ft versus the Phase 5A coastal reference. The unverified-availability astronomical sensitivity has MAE 0.0894 ft and is not causal evidence.
At 12 h, adding issue-time harmonics to MAUL1 changes MAE by -0.0002 ft versus Phase 5A MAUL1-only. The tidal/coastal candidate changes MAE by +0.0001 ft versus the Phase 5A coastal candidate; the full river/coastal candidate changes it by +0.0005 ft. The Phase 5A river-only comparator MAE is 0.1621 ft. The calibration-fitted gate changes paired MAE by +0.0415 ft versus the Phase 5A coastal reference. The unverified-availability astronomical sensitivity has MAE 0.1561 ft and is not causal evidence.
At 24 h, adding issue-time harmonics to MAUL1 changes MAE by -0.0000 ft versus Phase 5A MAUL1-only. The tidal/coastal candidate changes MAE by -0.0010 ft versus the Phase 5A coastal candidate; the full river/coastal candidate changes it by -0.0000 ft. The Phase 5A river-only comparator MAE is 0.2159 ft. The calibration-fitted gate changes paired MAE by +0.0245 ft versus the Phase 5A coastal reference. The unverified-availability astronomical sensitivity has MAE 0.2157 ft and is not causal evidence.

The calendar-harmonic model adds little beyond MAUL1 history. Adding tidal/coastal features shifts holdout MAE only slightly relative to Phase 5A, while the full multivariable and issue-time gate do not consistently improve the coastal reference. The gate selected a zero variability threshold in each horizon, so it almost always issued the advanced periodic candidate; this failed to retain the stronger Phase 5A coastal model. The 6-hour coastal+tidal improvement is small and must not be treated as robust without prospective verification. The archived astronomical sensitivity modestly changes scores but relies on unverified future valid-time archive values and cannot justify a forecast feature.


The `maul1_astro_retrospective` method is not a causal forecast and is kept out of the primary table above. Its holdout sensitivity is in `summary.json`; compare its paired sample size before interpreting it against the harmonic-only candidate.


## Tidal features and availability

The causal periodic candidate uses UTC 24-hour and 12.42-hour sinusoids and a 14.765-day spring-neap phase proxy. These are calendar harmonics, not a calibrated local tide prediction; NWCL1 phase is not transferred to MAUL1. NOAA CO-OPS prediction rows use MLLW and pass an exact datum check, but the archive has no capture timestamp or issue-time availability ledger. Therefore target-valid-time astronomical values are isolated in `maul1_astro_retrospective`, excluded from all causal model selection and gating. Holdout rows with a matched retrospective prediction delta: 99546 of 99546 horizon rows. Their scores are not an advance forecast skill estimate.

## Gating and rising-water errors

The issue-time gate selects persistence below a calibration-only variability threshold and the chosen advanced candidate above it. Missing issue features fall back to persistence. Rising-water strata use target outcomes for verification only.

| Horizon | Method | Rising n | Mean signed error (ft) | Underforecast frequency | Mean underforecast (ft) | P99 abs error (ft) |
|---:|---|---:|---:|---:|---:|---:|
| 6 h | persistence_ft | 15580 | -0.18161842105263157 | 1.0 | 0.18161842105263157 | 0.43500000000000005 |
| 6 h | maul1_only_ft | 15580 | -0.07321000597398382 | 0.784788189987163 | 0.1079959972318597 | 0.35930101133609205 |
| 6 h | maul1_plus_coastal_ft | 15580 | -0.02921978768232249 | 0.6410141206675225 | 0.07204739768819214 | 0.25719735620699435 |
| 6 h | maul1_plus_river_ft | 15580 | -0.0705638184431752 | 0.7745827984595636 | 0.10667101986571452 | 0.3581276706402273 |
| 6 h | maul1_periodic | 15580 | -0.07312691445497453 | 0.7859435173299102 | 0.1076302994006361 | 0.3580854254575133 |
| 6 h | maul1_coastal_tidal | 15580 | -0.03353143125015951 | 0.6690629011553273 | 0.07302826207411289 | 0.26203202386545793 |
| 6 h | full_multivariable | 15580 | -0.021504829661507158 | 0.6013478818998717 | 0.06876834827289026 | 0.2532398626186503 |
| 6 h | gated_full | 15580 | -0.07424404418154718 | 0.7878690629011553 | 0.10864209872517655 | 0.3650161892769382 |
| 12 h | persistence_ft | 15824 | -0.24739857178968655 | 1.0 | 0.24739857178968655 | 0.655 |
| 12 h | maul1_only_ft | 15824 | -0.13334368582799497 | 0.8147750252780587 | 0.1814605353092668 | 0.6136718917525101 |
| 12 h | maul1_plus_coastal_ft | 15824 | -0.08025519599031702 | 0.7282608695652174 | 0.1402954631478734 | 0.4817275145461453 |
| 12 h | maul1_plus_river_ft | 15824 | -0.1263669518551396 | 0.798407482305359 | 0.17811885450141418 | 0.6083314879738783 |
| 12 h | maul1_periodic | 15824 | -0.13322195914914625 | 0.8151541961577351 | 0.18116931197474986 | 0.613442868318418 |
| 12 h | maul1_coastal_tidal | 15824 | -0.07463040152411972 | 0.7120197168857432 | 0.13765515965216008 | 0.47478114731956417 |
| 12 h | full_multivariable | 15824 | -0.06764919719477518 | 0.6905333670374115 | 0.13508014762905085 | 0.47224224232464934 |
| 12 h | gated_full | 15824 | -0.1342653713821367 | 0.8176188068756319 | 0.18167042471610886 | 0.6142054049584068 |
| 24 h | persistence_ft | 16004 | -0.2431301549612597 | 1.0 | 0.2431301549612597 | 0.9500000000000002 |
| 24 h | maul1_only_ft | 16004 | -0.17578214964960098 | 0.7980504873781554 | 0.24320876394513322 | 0.8479180059028716 |
| 24 h | maul1_plus_coastal_ft | 16004 | -0.15763745328842788 | 0.7794926268432891 | 0.23359976319185266 | 0.8154871196509176 |
| 24 h | maul1_plus_river_ft | 16004 | -0.163555848793778 | 0.7696200949762559 | 0.2403001581384053 | 0.8596365531453485 |
| 24 h | maul1_periodic | 16004 | -0.17578061390806465 | 0.7975506123469133 | 0.24335638544429578 | 0.8492519502163033 |
| 24 h | maul1_coastal_tidal | 16004 | -0.1228651515237736 | 0.7148837790552361 | 0.21771669837609103 | 0.777614044090596 |
| 24 h | full_multivariable | 16004 | -0.13780010413106003 | 0.7426893276680829 | 0.2251865809346299 | 0.7953572528793453 |
| 24 h | gated_full | 16004 | -0.17629010985060714 | 0.7993001749562609 | 0.24324857529130012 | 0.8492519502163033 |

## Robustness and uncertainty

Annual metrics, Phase 3B response-event group metrics, Phase 4 issue-state strata, interval coverage, model parameters, and paired issue forecasts are in the adjacent JSON/CSV files. Event grouping avoids interpreting overlapping hourly forecasts as independent events. Empirical 80% symmetric residual intervals are calibrated from forward OOF calibration predictions for Phase 5B models and calibration residuals for Phase 5A comparators.

No verified lead-time capture metadata exists for the archived NOAA prediction product. The archive does not provide reliable operational forecast availability; no model here is eligible for deployment. The 2023-onward scores are reused retrospective benchmarks, not pristine independent model-selection results. A prospective research trial should freeze this code, issue forecasts prospectively at fixed UTC hours, archive the full input snapshot and receipt time, and verify against future completed MAUL1 bins after a predeclared period; remain free and non-operational.

## Historical case comparisons

The case-level table reports matched-window MAE and rising-outcome underforecast frequency. August 2016 and Beta 2020 are calibration-era examples; November 2024 and April 2025 are part of the reused historical benchmark, not pristine model-selection cases.

| Case | Period class | Horizon | Phase 5A coastal MAE | Phase 5B coastal+tide MAE | Phase 5B full MAE | Phase 5B gated MAE |
|---|---|---:|---:|---:|---:|---:|
| flood-2016 | calibration (not independent) | 12 h | 0.217190700950533 | None | None | None |
| flood-2016 | calibration (not independent) | 24 h | 0.2837371831249924 | None | None | None |
| flood-2016 | calibration (not independent) | 6 h | 0.124032262608358 | None | None | None |
| beta-2020 | calibration (not independent) | 12 h | 0.117478262344201 | 0.11329859267039319 | 0.11853056294230963 | 0.15778073207805904 |
| beta-2020 | calibration (not independent) | 24 h | 0.18168268029838278 | 0.184049843037789 | 0.18933777520385262 | 0.2855148444708807 |
| beta-2020 | calibration (not independent) | 6 h | 0.08300777867229508 | 0.08287658544362217 | 0.08420988557658098 | 0.07695763864190686 |
| front-2024-11 | holdout | 12 h | 0.13646248326548968 | 0.13587058683737885 | 0.13808930143300474 | 0.16046577673338927 |
| front-2024-11 | holdout | 24 h | 0.21542074745921377 | 0.20750834099691431 | 0.21628762598189966 | 0.26148594037206085 |
| front-2024-11 | holdout | 6 h | 0.07287081035752367 | 0.07340629128636016 | 0.0745488889508294 | 0.08130161179091923 |
| front-2025-04 | holdout | 12 h | 0.1052572153988926 | 0.1175787867649552 | 0.1023296946423718 | 0.17464453390250206 |
| front-2025-04 | holdout | 24 h | 0.23272433857620764 | 0.2640427561731016 | 0.22856576110692658 | 0.31226951275897935 |
| front-2025-04 | holdout | 6 h | 0.047439421575928335 | 0.05335587110810958 | 0.04718683346794946 | 0.08814176185689679 |

Additional post-2022 cases are selected by the largest positive 24-hour outcome changes with non-overlapping 72-hour windows; because selection uses future outcomes, these examples describe retrospective outcomes and do not measure operational selection skill.

- 2024-09-11T11:00:00Z: observed +1.420 ft in 24 h; Phase 5A coastal 3.766295908185226; Phase 5B periodic 3.5173148652302557, coastal+tide 3.796184848287245, full 3.7700653520344676.
- 2024-04-06T04:00:00Z: observed +1.305 ft in 24 h; Phase 5A coastal 0.8834465576606182; Phase 5B periodic 0.884076726403637, coastal+tide 0.9295723273730634, full 0.9167685123705729.
- 2024-01-08T06:00:00Z: observed +1.300 ft in 24 h; Phase 5A coastal 1.6116865249836372; Phase 5B periodic 1.5679163235037499, coastal+tide 1.6584362498093659, full 1.651459339348586.
- 2024-02-03T01:00:00Z: observed +1.300 ft in 24 h; Phase 5A coastal 1.478640653556252; Phase 5B periodic 1.4797926398058412, coastal+tide 1.541251882769416, full 1.5015101536643283.
- 2026-06-03T19:00:00Z: observed +1.250 ft in 24 h; Phase 5A coastal 2.451003638612327; Phase 5B periodic 2.2358480412432216, coastal+tide 2.4998855312613832, full 2.430642375908925.
- 2024-09-04T18:00:00Z: observed +1.165 ft in 24 h; Phase 5A coastal 3.3862121257575737; Phase 5B periodic 3.0715975204686488, coastal+tide 3.431131948679767, full 3.4171004728167627.
