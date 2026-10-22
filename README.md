# REIT7820 - EV Charging agent

Your agent for the Smart Mobility Agent Collective: an MCP server that already
runs on real Queensland open data. The tools are yours to build.

## Files

```
src/agents/charging.py         your agent - this is where you work
src/eval/tasks.charging.json   your evaluation cases
prompt.txt                     a question for ask.py - write your own
src/descriptions.md            your v1 and v2 tool descriptions - a submission
src/data.py                    open-data fetching, cached
src/                           the rest is shared plumbing: read it, don't edit it
application/                   the console, which calls your agent the way the Orchestrator will
.env                           your keys - git-ignored, never commit it
logs/                          usage.jsonl (every Claude call) and W&B files
REIT7820_mcp_spec_v1.0.1.md    the contract your agent must satisfy
mcp-agent.toml                 how your UQCloud zone runs your agent
DEPLOY.md                      putting your agent online on your zone
```

## Setup

Install Docker Desktop, then create `.env` at the repository root:

```bash
ANTHROPIC_API_KEY=...
WANDB_API_KEY=...
WANDB_PROJECT=reit7820-charging     # optional, defaults to reit7820-eval
WANDB_ENTITY=...                 # optional, your W&B team
```

Both keys are required. Without a working `ANTHROPIC_API_KEY` nothing starts:
not your agent, the console, `ask.py` or the evaluation. Without
`WANDB_API_KEY` the evaluation does not run.

## Run

```bash
docker compose up -d --build                        # your agent on :8000, the console on :8080
docker compose exec charging python preflight.py --fetch    # check Python, keys and datasets
open http://localhost:8080                          # the console
```

If `up` reports that your agent failed to start, `docker compose logs charging`
says why. It is usually a missing or rejected key.

```bash
docker compose up -d --build charging      # after you edit your code - a plain restart runs the old code
docker compose logs -f charging            # your agent's log
docker compose ps                       # what is running
docker compose down                     # stop
```

## Build your agent

Open `src/agents/charging.py`:

1. Set `AGENT_NAME` to `smac-charging-<chose a name that best describe your proposed methods>`, and `VERSION`.
2. Read `find_nearest_charger`, the worked example. Then replace it with your own tools:
   one to five, named verb-first in snake_case.
3. Rebuild with `docker compose up -d --build charging`.

The Orchestrator never reads your code. It chooses tools from their names,
descriptions and parameter descriptions alone, and their quality is graded. A
good description says what the tool does, where it is valid, how accurate the data is
is, and what it does **not** do. Record v1 and v2 of each in `src/descriptions.md`.

- Return through `respond(...)`, so every response carries `sources`.
- Decline what you cannot answer with `out_of_scope(...)`. Never invent an answer.
- Compute numbers in code, and let the model only write prose about them. For example, use
  `geocode_place` instead of letting a model recall a coordinate.

## Evaluate

Each case in `src/eval/tasks.charging.json` holds a prompt, the tools you expect
called with their arguments, and the output you expect back:

```json
{
  "prompt": "Where can I charge my EV near the University of Queensland, St Lucia?",
  "tools": [
    {"name": "geocode_place", "input": {"place": "University of Queensland St Lucia"}},
    {"name": "find_nearest_charger",
     "input": {"lat": -27.4981423, "lon": 153.0111536, "max_results": 1}}
  ],
  "output": {"nearest": [{"name": "Brisbane", "distance_m": 9311}]}
}
```

Numbers must match exactly. Text matches if your string appears anywhere in the
response. Derive every expected value from the dataset yourself, never from your
agent's output. Include a question you should decline and one malformed input.

```bash
docker compose exec charging python eval/run_eval.py --tasks eval/tasks.charging.json
```

W&B logging is required: every run is logged to your W&B project, so runs sit
side by side. Each run first checks your Claude API key with one small call and
opens the W&B run. Then it runs the cases and logs them. If either key is
missing or rejected, it stops before the first case.

## Ask your agent anything

Write a question in `prompt.txt`, then:

```bash
docker compose exec -T charging python ask.py < prompt.txt
```

A model sees only your tools' names and descriptions, picks which to call, and
answers from what they return, which is how the Orchestrator will use your agent.
Each step is printed in order: the tool chosen and why, its arguments, what it
returned, and then the answer. Add `--model claude-sonnet-5` after `ask.py` to
change the model doing the choosing; your agent's own model stays the same.

The question, the tool calls and the answer are printed in colour. To turn
colour off, for example when saving the output to a file, add `-e NO_COLOR=1`
after `exec`.

## Handshake test

The conformance check from the spec, and a hurdle for the Showcase. It connects
to your agent the way the Orchestrator does and runs six checks. Put the
`smac-handshake-test/` folder in the repository root, then:

```bash
docker compose run --rm handshake
```

It ends with `HANDSHAKE PASSED`, or tells you what to fix. It also writes
`handshake_report.json`, which you commit as your proof.

Once your agent is on your zone, run the same test against its public address
with your token: see step 7 of [DEPLOY.md](DEPLOY.md).

## Deploy to your zone

Your agent goes online on your own UQCloud zone, which is where the
Orchestrator calls it at the Showcase. Follow [DEPLOY.md](DEPLOY.md).

Find your zone name, `reit7820-xxxxxxxx`, on
[coursemgr](https://coursemgr.uqcloud.net/reit7820). Then:

```bash
# 1. Log in with your UQ username and password (nothing shows as you type it)
ssh <uq-username>@reit7820-xxxxxxxx.zones.eait.uq.edu.au

# 2. On the zone: save your Claude API key (sudo asks for your password first,
#    then the key)
sudo mcp-env set ANTHROPIC_API_KEY

# 3. Make the zone's deploy key. Paste the ssh-ed25519 line into the setup form
#    (choose Deploy key) and wait for confirmation
sudo mcp-deploy --keygen

# 4. Deploy from your repo's default branch, with the git@ address
sudo mcp-deploy git@github.com:<owner>/<repo>.git
systemctl status mcp-agent              # look for: active (running)

# 5. Leave the zone
exit
```

Then run the handshake test with your token, on the zone or your laptop
(step 7 of DEPLOY.md). After the
first deploy that succeeds, `sudo mcp-deploy` on its own deploys your latest
commit.

## Choose the model

Your agent runs on `claude-haiku-4-5` unless you choose another tier:
`claude-sonnet-5` or `claude-opus-5`. The model in use is
reported by `health` and recorded with every W&B run.

To set it until you change it, add a line to `.env`, then restart:

```bash
LLM_MODEL=claude-sonnet-5
```

```bash
docker compose up -d charging
```

To use it for one run only, set it on the command line:

```bash
LLM_MODEL=claude-sonnet-5 docker compose up -d charging
docker compose exec charging python eval/run_eval.py --tasks eval/tasks.charging.json
docker compose up -d charging              # back to the .env setting
```

Every Claude call your agent makes is appended to `logs/usage.jsonl`, with its
model, tokens and latency.

## Station data (EV-RouteCharge)

`assess_ev_trip_feasibility` draws on two openly licensed sources:

| Source | What it gives | Licence |
|---|---|---|
| Open Charge Map, pinned in `src/snapshots/ocm_qld.json` | Stations in and around Queensland, with rated power, connector types and access | CC BY 4.0 |
| Queensland Government Electric Super Highway list (TMR) | The state's designated corridor sites, used to flag OCM records (`is_qesh`) | CC BY 4.0 |

The agent reads the OCM snapshot rather than calling the API, so it needs no OCM
key to run, and the dataset stays fixed across evaluation runs. The snapshot's
date is reported in every response. To refresh it, put `OCM_API_KEY` in `.env`
and, from the repository root:

```bash
python src/data.py refresh-ocm
```

A refresh can change which station ranks first, so re-derive the evaluation's
expected values afterwards. This checks every trip case in
`src/eval/tasks.charging.json` against the data, without consulting the agent:

```bash
python src/eval/derive_ground_truth.py
```
