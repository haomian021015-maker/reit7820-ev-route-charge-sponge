# Sensitivity of the agent's answers to its assumptions

860 trips: 172 place pairs at least 30 km apart (straight line), each with a remaining range of 30%, 50%, 70%, 90%, 120% of the agent's road estimate; full range 400 km. Baseline verdicts: feasible 172, requires_charging 678, infeasible 10.

## 1. If an assumption were different

| Change from the baseline | Same verdict | Same first stop (trips needing one in both) |
|---|---|---|
| Road factor 1.24 (observed median, OSRM) | 860/860 (100%) | 633/678 (93%) |
| Road factor 1.187 (observed lower quartile) | 859/860 (100%) | 591/678 (87%) |
| Road factor 1.363 (observed upper quartile) | 859/860 (100%) | 639/677 (94%) |
| Consumption 15 kWh/100 km (efficient car) | 860/860 (100%) | 653/678 (96%) |
| Consumption 22 kWh/100 km (large SUV) | 860/860 (100%) | 657/678 (97%) |
| No range reserve (0%) | 859/860 (100%) | 589/678 (87%) |
| Range reserve 20% | 686/860 (80%) | 590/676 (87%) |
| Car limited to 50 kW charging | 860/860 (100%) | 311/678 (46%) |

## 2. 'Can I make it without charging?' against real driving distance

Each trip's verdict compared with the same reserve applied to the OSRM driving distance.

| Outcome | Trips |
|---|---|
| Agrees with the real-road verdict | 823 |
| Says a stop is needed, real road says not (cautious) | 0 |
| Says feasible, real road says not (unsafe) | 37 |

Of the 172 trips the agent calls feasible, 37 (22%) are not feasible by the real road with the same reserve. In this grid a feasible verdict always has 8% to spare on the agent's own estimate, so the share depends on that margin; the routes involved are the ones the road factor underestimates (see results/road-factor).

Unsafe cases: University of Queensland St Lucia to Esk, Queensland at 101.2 km; Brisbane City to Esk, Queensland at 101.2 km; Toowoomba to Caboolture at 174.6 km; Toowoomba to Caloundra at 225.4 km; Toowoomba to Maroochydore at 236.1 km; Toowoomba to Noosa Heads at 267.4 km; Toowoomba to Nambour at 224.7 km; Toowoomba to Kilcoy, Queensland at 142.6 km; Toowoomba to Boonah at 136.3 km; Toowoomba to Beaudesert at 176.4 km; Ipswich to Beaudesert at 74.0 km; Gatton to Caboolture at 132.6 km; Gatton to Caloundra at 187.1 km; Gatton to Maroochydore at 201.4 km; Gatton to Noosa Heads at 237.4 km; Gatton to Nambour at 193.4 km; Gatton to Boonah at 98.2 km; Gatton to Beaudesert at 132.7 km; Surfers Paradise to Boonah at 111.5 km; Surfers Paradise to Beaudesert at 65.6 km; Coolangatta to Boonah at 132.6 km; Coolangatta to Beaudesert at 88.7 km; Beenleigh to Boonah at 91.1 km; Cleveland, Queensland to Redcliffe, Queensland at 57.1 km; Cleveland, Queensland to Caloundra at 127.9 km; Cleveland, Queensland to Boonah at 119.0 km; Redcliffe, Queensland to Caloundra at 74.4 km; Redcliffe, Queensland to Esk, Queensland at 106.6 km; Caboolture to Esk, Queensland at 86.0 km; Caloundra to Esk, Queensland at 134.3 km; Maroochydore to Esk, Queensland at 145.2 km; Noosa Heads to Kilcoy, Queensland at 124.8 km; Noosa Heads to Esk, Queensland at 178.7 km; Nambour to Kilcoy, Queensland at 82.6 km; Nambour to Esk, Queensland at 135.2 km; Kilcoy, Queensland to Esk, Queensland at 56.0 km; Boonah to Springfield Central at 61.7 km

## 3. Ranking by time added against simple alternatives

678 trips that need a stop. Extra time = time the alternative's pick adds minus the time the agent's pick adds, both under the agent's own time model (detour at 60 km/h plus charging at the charger's rated power).

| Alternative rule | Picks the same stop | Median extra minutes | 90th percentile | Maximum |
|---|---|---|---|---|
| Nearest to the origin | 126/678 (19%) | 6.1 | 17.9 | 54.7 |
| Least detour | 271/678 (40%) | 1.8 | 14.2 | 295.3 |
| Most powerful charger | 426/678 (63%) | 0.0 | 16.0 | 40.1 |
