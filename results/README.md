# Results - evidence index for the report

Every result folder here was produced by a script in `src/eval/`, from data in
this repository, and can be re-run. Costs are Claude API spend.

## Agent correctness

| Evidence | What it shows | Key figures | Report section |
|---|---|---|---|
| `src/eval/tasks.charging.json`, `run_eval.py` | The 12 evaluation cases written while building the agent | 12/12 pass | Evaluation: functional tests |
| `src/eval/tasks.heldout.json`, `build_heldout_tasks.py` | 24 new cases written for the replication, expected values derived from the data | 24/24 pass on v3 and v4 | Evaluation: functional tests |
| `src/eval/derive_ground_truth.py` | Expected values re-derived without importing the agent | 7/7 original trip cases agree | Method: ground truth |
| `handshake_report.json` | Course conformance test against the public zone | 6/6 checks | Implementation: deployment |

## Data and assumptions

| Folder | Question | Key figures | Report section |
|---|---|---|---|
| `station-audit/` | What the station data holds and lacks | 148 OCM sites; 139 public and in service + 1 TMR-only = 140 candidates; median record age 3.2 years; 16/17 TMR sites matched within 150 m; no source gives live availability or price | Data |
| `road-factor/` | How good is road distance = straight line x 1.3? (OSRM, 190 SEQ pairs) | Observed ratio median 1.242 (IQR 1.188-1.362); the factor overestimates by 4.7% at the median; underestimates by up to 41%, worst on winding routes (Esk, Kilcoy) | Method: assumptions; Limitations |
| `sensitivity/` | Do answers depend on the constants? Are feasible verdicts safe on real roads? Does ranking by time added matter? | Verdicts unchanged in at least 859 of 860 trips for road factor 1.19-1.36 and consumption 15-22, but the first stop changes in 6-13% of trips; 22% of feasible verdicts fail on the real road (8% margin); nearest-station rule picks the same stop in 19% of trips and adds a median 6.1 min | Results: design evaluation; Limitations |

## Prompt-architecture experiment (the thesis variable)

All runs: router answers a question through the console's router loop; scored on
six checks (`tool_ok`, `args_ok`, `coords_ok`, `stop_ok` by rule; `verdict_ok`,
`faithful` by a judge model, audited by hand). Statistics: 95% Wilson intervals,
permutation test stratified by question, Bonferroni across pairwise comparisons.

| Folder | Design | Passed every check: rules only / + examples / + procedure | Report section |
|---|---|---|---|
| `prompt-architecture-20261020/` | Experiment 1: Haiku 4.5, 12 original questions x 3 repeats x 3 prompts = 108 runs ($3.10) | 42% / 50% / 67%; procedure vs rules p = 0.046 (suggestive). Coordinates from memory 9/21 trip calls with rules only, 0 otherwise (p = 0.008-0.009) | Results 1 |
| `prompt-architecture-heldout-20261102/` | Replication: same design, 24 held-out questions = 216 runs ($6.57) | 46% / 74% / 67%; both treatments beat rules only (p < 0.001, p = 0.008). No recalled coordinates in any condition | Results 2 |
| `prompt-architecture-pooled/` | Experiments 1 + 2 analysed together, 36 questions = 324 runs | 44% / 66% / 67%; both p < 0.001; examples and procedure do not differ (p = 1.0) | Results 2 |
| `prompt-architecture-sonnet-20261102/` | Sonnet 5.5 as router, held-out questions, rules only and + examples = 144 runs ($5.89) | 82% / 93% (p = 0.011). In a pilot, Sonnet 5.5 declined all 4 runs of the + procedure prompt (`stop_reason: refusal`), so that condition was not run | Results 3: generalisation across models |
| `descriptions-v4-original/`, `descriptions-v4-heldout/`, `descriptions-v4-comparison/` | Rules-only router against the v4 tool descriptions, both question sets = 108 runs ($3.34) | Passed every check 44% (v3) vs 38% (v4), p = 0.37. Targeted question fixed (0/3 to 3/3 right verdicts), but recalled coordinates appeared on 3 new questions (9/9 runs) | Results 4: tool descriptions |

Judge audits: `prompt-architecture-20261020/README.md` (17/17 flags confirmed, 1
miss in 12). The replication's audit sample is drawn and scored with
`src/eval/make_audit_sheet.py`.

Comparisons across folders that were not interleaved in one session (Haiku vs
Sonnet; v3 vs v4) use the same questions and seeds but were run in different API
sessions.

## References

- Model Context Protocol specification, revision 2025-11-25. https://modelcontextprotocol.io/specification
- Schick, T. et al. (2023). Toolformer: Language Models Can Teach Themselves to Use Tools. NeurIPS 36. arXiv:2302.04761
- Yao, S. et al. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. ICLR 2023. arXiv:2210.03629
- Patil, S. G., Zhang, T., Wang, X., Gonzalez, J. E. (2024). Gorilla: Large Language Model Connected with Massive APIs. NeurIPS 2024. arXiv:2305.15334
- Zheng, L. et al. (2023). Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. NeurIPS 2023 Datasets and Benchmarks. arXiv:2306.05685
- Ballou, R. H., Rahardja, H., Sakai, N. (2002). Selected country circuity factors for road travel distance estimation. Transportation Research Part A 36(9), 843-848. doi:10.1016/S0965-8564(01)00044-1
- Measures to resolve range anxiety in electric vehicle users (2022). International Journal of Low-Carbon Technologies. doi:10.1093/ijlct/ctac100
- Ovchinnikov, A., Forestell, D. (2026). From Range Anxiety to Charge Anxiety. Service Science. doi:10.1287/serv.2024.0137
- Brown, T. et al. (2020). Language Models are Few-Shot Learners. NeurIPS 2020. arXiv:2005.14165
- Wei, J. et al. (2022). Chain-of-Thought Prompting Elicits Reasoning in Large Language Models. NeurIPS 2022. arXiv:2201.11903
- Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. JASA 22(158), 209-212
