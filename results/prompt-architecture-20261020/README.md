# Prompt architecture experiment - 2026-10-20

Purpose 2 of the proposal: does the prompt architecture of the model calling this
agent change how reliably it uses the agent's tools?

- **Independent variable:** the router's system prompt - `zero_shot` (the console's
  `ROUTER_SYSTEM`, verbatim), `few_shot` (baseline + four worked examples on trips
  outside the task set), `scaffold` (baseline + a five-step procedure). Texts in
  [`src/eval/prompts/`](../../src/eval/prompts/).
- **Held constant:** router model `claude-haiku-4-5`; agent `smac-charging-tripfeasibility`
  0.2.0 and its tool descriptions ([`tool_menu.txt`](tool_menu.txt)); OCM snapshot of
  2026-10-15; the 12 questions in `src/eval/tasks.charging.json`; the console's router
  loop, including its 4-decision budget and 2,500-character view of each tool result.
- **Design:** 12 questions x 3 conditions x 3 repeats = 108 runs, interleaved in a
  seeded random order (seed 20261020).
- **Scoring:** rule-based `tool_ok`, `args_ok`, `coords_ok`, `stop_ok`; `verdict_ok` and
  `faithful` read by a judge model (`claude-opus-5-5`, effort medium, structured output).
  Definitions in [`src/eval/run_prompt_experiment.py`](../../src/eval/run_prompt_experiment.py).
- **Cost:** router $0.99, judge $2.11.

## Files

| File | Contents |
|---|---|
| `runs.jsonl` | One record per run: question, every tool call with its full result, the answer, each score, the judge's findings, latency and router token usage |
| `summary.md` / `summary.json` | Rates per condition and per question |
| `analysis.md` | 95% Wilson intervals and stratified permutation tests (`src/eval/analyse_prompt_experiment.py`) |
| `tool_menu.txt` | Exactly what the router - and the judge - could read about the tools |

## Results

| Metric | zero_shot | few_shot | scaffold |
|---|---|---|---|
| coords_ok - no guessed coordinate | 57% (12/21) | 100% (18/18) | 100% (20/20) |
| args_ok - no invented or wrong argument | 95% (20/21) | 83% (15/18) | 100% (20/20) |
| tool_ok | 89% | 83% | 92% |
| stop_ok | 80% (12/15) | 87% (13/15) | 88% (15/17) |
| verdict_ok | 92% | 92% | 97% |
| faithful | 50% | 58% | 69% |
| **all_ok** | **42%** | **50%** | **67%** |
| router cost per run | $0.0071 | $0.0111 | $0.0092 |
| median latency | 8.0 s | 8.0 s | 10.0 s |

Only `coords_ok` survives a Bonferroni correction (p = 0.008-0.009 against a 0.017
threshold): the baseline router looked up the origin and filled in the destination
from memory in 9 of 21 trip calls - the same recalled Toowoomba coordinate six times,
Melbourne's three times - and neither treatment did so once. `all_ok` for scaffold
over zero-shot (+25 points, p = 0.046) is suggestive, not established.

## How this run came to be, in order

1. **Pilot, 9 runs (not included).** Showed two flaws, both fixed before the main run:
   the judge, shown only tool results, flagged statements that restate a tool
   *description* (e.g. "typical mid-size EVs use around 18 kWh per 100 km"), so it is
   now given the tool menu; and a router passed a coordinate it had recalled rather
   than looked up, which no check caught, so `coords_ok` was added. The fixed judge
   re-graded the same 9 saved answers before the main run.
2. **Main run, 108 runs.** No run errored or hit the step limit; the judge graded all 108.
3. **W&B upload.** A wrong method name stopped the upload after the first condition.
   All three were re-uploaded from the saved files (`--relog`); the partial run was
   moved to group `prompt-architecture-20261020-053044-interrupted` and tagged, not deleted.
4. **Re-score.** Station names are now matched as whole words ("east", from East
   Brisbane, is inside "at least"). Re-scoring the saved runs (`--rescore`, no model
   called) changed no score; all 40 `stop_ok` hits contain the full station name.

## Checking the judge

- Pilot: all 8 flags checked by hand against the tool output; all 8 correct.
- Main run: 12 answers sampled at random (4 per condition, seed 11) and checked by hand.
  All 9 flags were correct. On whether an answer was faithful, I agreed with the judge
  on 11 of 12; the one disagreement is a missed flag - scaffold Q11 repeat 1 claims the
  tool "would produce meaningless results" at zero consumption, a guess about its
  behaviour (it in fact rejects the value) - and it favours the scaffold condition.
- So far, then, every flag the judge raised was right (17/17), and it missed 1 in 12.

## Sensitivity

The pre-registered rubric requires an out-of-coverage refusal to come from a tool.
Accepting a refusal made from the coverage stated in the tool descriptions instead
leaves `all_ok` unchanged in every condition (42% / 50% / 67%).

## Limitations

- 12 questions and 36 runs per condition: a pilot-scale sample.
- One router model. Whether the effects hold for a stronger model is untested.
- The judge is itself a model; see its audit above.
- Few-shot Example 2 distinguishes charging time from added time - which is what a
  correct answer does - but it was written after the baseline was seen to confuse them.
- The router chooses its own place-lookup strings ("UQ St Lucia" resolves to the CityCat
  terminal), so origins, and sometimes the first recommended stop, differ between runs;
  `stop_ok` is therefore scored against each run's own tool result.

## What this means for the agent (changes for after the Showcase)

- `consumption_kwh_per_100km` does not say it must be greater than zero, though the tool
  rejects zero; routers guessed at its behaviour in every condition.
- `completes_trip_after_stop: null` (unknown, no battery size given) was read as "no" in
  all three conditions; an explicit value such as `"unknown: full_range_km not given"`
  would remove the ambiguity.
- Asked a question that flags optional details as missing ("I never said how big the
  battery is"), routers often declined outright - 3/3 runs at zero-shot and few-shot,
  1/3 with the scaffold - although the description says the verdict does not need them.
- The response puts `data_gaps` and the agent's own explanation after 2,500 characters,
  so a router that truncates there never sees them; the most important fields should come first.
