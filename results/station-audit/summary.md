# Station data audit

Open Charge Map snapshot taken 2026-10-15T18:30:22+10:00 (148 sites, open-data records only, licence: Open Charge Map contributors via api.openchargemap.io, CC BY 4.0); TMR Electric Super Highway list: 17 rows, 17 active.

## What survives the agent's filters

| Step | Sites |
|---|---|
| OCM snapshot | 148 |
| Public access (private sites dropped) | 142 |
| Public and in service (not operational / temporarily unavailable dropped) | 139 |
| Plus TMR highway sites with no OCM twin (no power or plug data) | 1 |
| **Candidate pool for a trip with no plug preference** | **140** |

## Access and status, all OCM sites

| Usage | Sites |
|---|---|
| Public - Membership Required | 113 |
| Public | 25 |
| Private - For Staff, Visitors or Customers | 5 |
| Public - Pay At Location | 3 |
| Privately Owned - Notice Required | 1 |
| Public - Notice Required | 1 |

| Status | Sites |
|---|---|
| Operational | 141 |
| Partly Operational (Mixed) | 3 |
| Not Operational | 2 |
| Unknown | 1 |
| Temporarily Unavailable | 1 |

## Fields filled, public in-service sites (n = 139)

| Field | Filled |
|---|---|
| name | 139/139 (100%) |
| address | 139/139 (100%) |
| operator | 130/139 (94%) |
| power_kw | 134/139 (96%) |
| connector_types | 137/139 (99%) |
| last_updated | 139/139 (100%) |
| status | 139/139 (100%) |

## Rated power, public in-service sites

| Band | Sites |
|---|---|
| AC slow, under 7.4 kW | 6 |
| AC, 7.4-22 kW | 6 |
| DC, 22-50 kW | 61 |
| DC fast, 50-150 kW | 48 |
| DC ultra-fast, over 150 kW | 13 |
| Not published | 5 |

Median rated power 50 kW; maximum 350 kW.

## Plug types offered, public in-service sites

| Plug | Sites offering it |
|---|---|
| CCS (Type 2) | 123/139 (88%) |
| CHAdeMO | 97/139 (70%) |
| Type 2 (Socket Only) | 55/139 (40%) |
| Type 2 (Tethered Connector) | 3/139 (2%) |
| Type I (AS 3112) | 2/139 (1%) |
| Type 1 (J1772) | 1/139 (1%) |
| Three Phase 5-Pin (AS/NZ 3123) | 1/139 (1%) |

## How recently each record was updated (public in-service sites)

| Last updated | Sites |
|---|---|
| Within 1 year | 7 |
| 1-3 years | 23 |
| 3-5 years | 100 |
| Over 5 years | 9 |

Median record age 3.2 years at snapshot time.

## Largest operators, public in-service sites

| Operator | Sites |
|---|---|
| Queensland Electric Super Highway | 40 |
| Evie | 29 |
| Chargefox | 25 |
| BP Pulse (AU) | 12 |
| (Unknown Operator) | 9 |
| Tesla (including non-tesla) | 7 |
| NRMA | 5 |
| (Business Owner at Location) | 4 |

## Agreement with the TMR Electric Super Highway list

16/17 active TMR sites have an OCM site within 300 m (the agent's matching radius); 16/17 within 150 m. TMR publishes no plug or power data (its plug column is empty), so OCM supplies both for matched sites.

| TMR site | Nearest OCM site | Distance m | OCM power kW |
|---|---|---|---|
| Rockhampton | Rockhampton QESH | 17 | 50 |
| Cairns | Cairns QESH | 18 | 50 |
| Springfield | Springfield QESH | 19 | 50 |
| Gatton | QESH Lawes (Gatton) | 20 | 50 |
| Cooroy | Cooroy Station | 27 | 50 |
| Tully | Tully QESH | 40 | 50 |
| Brisbane | North Shore Hamilton Station [QLD Electric Superhighway] | 40 | 50 |
| Mackay | Mackay QESH | 45 | 50 |
| Maryborough | Maryborough QESH | 52 | 50 |
| Coolangatta | Bilinga QESH (Coolangatte Airport) | 53 | 50 |
| Childers | Childers QESH | 65 | 50 |
| Miriam Vale | Miriam Vale QESH | 65 | 50 |
| Townsville | Townsville QESH | 68 | 50 |
| Toowoomba | Charlton QESH | 83 | 50 |
| Bowen | Bowen QESH | 95 | 50 |
| Carmila | Carmila QESH | 147 | 50 |
| Marlborough | Marlborough QESH | 4208 | 50 |

## What no source provides

- Live availability (whether a plug is free now): OCM status means 'generally operational'.
- Pricing.
- Per-plug power: OCM gives one rating per site, used for every plug there.
- The vehicle's charging curve: charging is modelled at a constant rate.
