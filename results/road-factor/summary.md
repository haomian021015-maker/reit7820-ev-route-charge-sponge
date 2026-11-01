# Road factor validation

190 place pairs among 20 South East Queensland places, measured 2026-11-02. Driving distance from the public OSRM demo router (OpenStreetMap data); straight line is the great-circle distance; the agent's estimate is straight line x 1.3. Positive error = the agent overestimates the drive.

| | Observed ratio road / straight | Agent's error |
|---|---|---|
| Median | 1.242 | +4.7% |
| Interquartile range | 1.188 - 1.362 | -4.6% to +9.5% |
| Min - max | 1.069 - 2.196 | -40.8% to +21.7% |
| Overestimates (safe side) | | 123/190 pairs |
| Within +/-10% | | 113/190 pairs |

## By straight-line distance

| Band | Pairs | Median ratio | Median error | Underestimates |
|---|---|---|---|---|
| under 30 km | 18 | 1.293 | +0.5% | 8 |
| 30-100 km | 108 | 1.268 | +2.5% | 45 |
| 100 km and over | 64 | 1.204 | +7.9% | 14 |

## Largest underestimates (the unsafe direction)

| From | To | Straight km | OSRM road km | Agent km | Error |
|---|---|---|---|---|---|
| University of Queensland St Lucia | Brisbane City | 3.4 | 7.5 | 4.4 | -40.8% |
| Caboolture | Esk, Queensland | 55.1 | 107.8 | 71.7 | -33.5% |
| Redcliffe, Queensland | Esk, Queensland | 68.3 | 132.1 | 88.8 | -32.8% |
| Nambour | Esk, Queensland | 86.6 | 147.0 | 112.6 | -23.4% |
| Nambour | Kilcoy, Queensland | 52.9 | 88.9 | 68.8 | -22.6% |

## Places as geocoded

| Query | Matched | lat | lon |
|---|---|---|---|
| University of Queensland St Lucia | University of Queensland, Chancellors Place, St Lucia, Brisbane, Queensland, 4067, Australia | -27.49814 | 153.01115 |
| Brisbane City | Brisbane City, Brisbane, Queensland, 4000, Australia | -27.47030 | 153.02582 |
| Toowoomba | Toowoomba, Queensland, 4350, Australia | -27.56102 | 151.95335 |
| Ipswich | Ipswich, Queensland, 4305, Australia | -27.61603 | 152.76083 |
| Gatton | Gatton, Queensland, Australia | -27.56153 | 152.27914 |
| Surfers Paradise | Surfers Paradise, Gold Coast, Queensland, Australia | -27.99899 | 153.42398 |
| Coolangatta | Coolangatta, Queensland, Australia | -28.16829 | 153.53875 |
| Beenleigh | Beenleigh, Brisbane, Queensland, 4207, Australia | -27.71595 | 153.20223 |
| Cleveland, Queensland | Cleveland, Redland City, Queensland, 4163, Australia | -27.52630 | 153.26673 |
| Redcliffe, Queensland | Redcliffe, Queensland, Australia | -27.22688 | 153.11300 |
| Caboolture | Caboolture, Queensland, 4510, Australia | -27.08393 | 152.95109 |
| Caloundra | Caloundra, Queensland, 4551, Australia | -26.79816 | 153.13544 |
| Maroochydore | Maroochydore, Queensland, 4558, Australia | -26.65565 | 153.09467 |
| Noosa Heads | Noosa Heads, Queensland, 4567, Australia | -26.40014 | 153.09105 |
| Nambour | Nambour, Queensland, Australia | -26.62573 | 152.95995 |
| Kilcoy, Queensland | Kilcoy, Queensland, Australia | -26.94172 | 152.56116 |
| Esk, Queensland | Esk, Queensland, Australia | -27.23987 | 152.42202 |
| Boonah | Boonah, Queensland, Australia | -27.99108 | 152.69622 |
| Beaudesert | Beaudesert, Queensland, Australia | -27.98856 | 152.99612 |
| Springfield Central | Springfield Central, Brisbane, Queensland, 4300, Australia | -27.68612 | 152.90378 |
