# Agent explanations against the agent's own figures

Every trip call with an explanation in the saved runs. Affected = the explanation states estimated_road_m x road_factor as a distance (the factor applied twice).

| Folder | Calls | Affected | Answers repeating it | ...of those judged unfaithful |
|---|---|---|---|---|
| prompt-architecture-20261020 | 56 | 12 | 1 | 1 |
| prompt-architecture-heldout-20261102 | 143 | 47 | 6 | 6 |
| prompt-architecture-sonnet-20261102 | 97 | 30 | 9 | 0 |
| descriptions-v4-original | 21 | 8 | 5 | 4 |
| descriptions-v4-heldout | 49 | 11 | 9 | 8 |

| Verdict | Calls | Affected |
|---|---|---|
| feasible | 84 | 42 (50%) |
| infeasible | 72 | 45 (62%) |
| requires_charging | 210 | 21 (10%) |
| All | 366 | 108 (30%) |
