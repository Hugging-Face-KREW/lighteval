# IFEval-Ko scoring

`src/lighteval/tasks/tasks/ifeval_ko/scoring.py` provides the independent Ko
strict/loose scorer. **Both direct scorer and registered-task regression pass
all 156 fixed-response cases**, matching the predeclared expectations, stored
original Ko results and a live run of the pinned original evaluator.

## Current validation status

- Direct scorer with the team's ported checkers: **156/156 cases**, strict **247/247 instructions + 156/156 prompts**,
  loose **247/247 instructions + 156/156 prompts**. Missing cases, unexpected
  scoring errors, decision differences and call-trace differences: **0**.
- Registered `ifeval_ko|0` task: **156/156 cases**, the same instruction/prompt
  decisions and four metrics through Registry, Doc conversion, `compute_sample`
  and native corpus aggregation. The scorer is also called directly in this run.
- Auxiliary inputs: **18/18** for both paths, each mode **10 normal returns + 8 expected exceptions**.
  These are excluded from the main metric denominators. Expected exceptions are
  contract checks, not successful normal scores.
- Policy/verifier tests: **11 passed**. Reference audit tests: **25 passed**.
- Ruff check and format check pass with Ruff `0.11.10`.
- Full pinned dataset formatting: **342/342 Docs**, preserving the original
  keys, prompts, kwargs and **481 ordered instruction occurrences**. This is
  dataset formatting validation, not model response scoring.

| Metric | Original Ko | Ported scorer | Registered task | Absolute error |
| --- | --- | --- | --- | --- |
| `prompt_level_strict_acc` | 71/156 | 71/156 | 71/156 | 0 |
| `inst_level_strict_acc` | 133/247 | 133/247 | 133/247 | 0 |
| `prompt_level_loose_acc` | 79/156 | 79/156 | 79/156 | 0 |
| `inst_level_loose_acc` | 142/247 | 142/247 | 142/247 | 0 |

The integrated task implementation was validated at
`21faccc0f27d35da37dd849894f37b0337b43edb`. The reference uses the audit's explicit
`isolated-source` import mode, retaining its original imports and source bytes;
the archived reference run used `full-package`. The direct scorer and registered
task use the team's ported checkers, without a reference fallback.

The registered-task results attached to
[PR #2](https://github.com/Hugging-Face-KREW/lighteval/pull/2#issuecomment-6718587652)
also matched by `case_id`, instruction index, and input/response hashes.
This optional attachment comparison is separate from locally executing the task.

## Remaining validation

English/French runtime regression, the 23-item model integration and the full
342-item model evaluation have not been run in this suite. Saved model responses
are required for those model evaluations: first compare all 23 prompts and 40
instructions, then proceed to all 342 prompts and 481 instructions after the
23-item checks pass and the full responses are available. Pass identical saved
assistant responses to both evaluators and record generation settings and errors.

The verifier checks dataset formatting through the task API. It does not run
`lighteval tasks inspect`; CLI inspection outputs remain separate PR evidence.

## Scoring behavior

The scorer follows Allganize IFEval-Ko's `ifeval_ko/utils.py` at revision
`54199e3801116897697babf341865741dcd06fc8`. It preserves NFC at each phase entry,
original prompt/kwargs, `if v` filtering,
optional second `build_description(prompt=prompt)`, all strict before all loose,
fresh checker per instruction per phase, indexed repeated IDs, eight ordered
loose candidates including duplicates, `strip()` eligibility, per-instruction OR
and per-prompt AND. Empty responses still construct checkers before returning
False. Empty instruction lists retain `all([]) == True`. External checker
exceptions propagate; internally handled exceptions retain the checker's result.

## `main.py` integration contract

```python
from lighteval.tasks.tasks.ifeval_ko.scoring import score_response

# In the Ko SampleLevelComputation.compute(doc, model_response, **kwargs):
return score_response(
    prompt=doc.query,
    instruction_id_list=doc.specific["instructions_id_list"],
    kwargs=doc.specific["kwargs"],
    response=model_response.final_text[0],
)
```

The return keys are `prompt_level_strict_acc` and `prompt_level_loose_acc`
(`bool`), and `inst_level_strict_acc` and `inst_level_loose_acc` (`list[bool]`
in original instruction order). `score_strict` and `score_loose` return
`PhaseResult(follow_instruction_list, follow_all_instructions)`.

Aggregate prompt Booleans by their mean. Flatten all instruction lists before
taking their mean, keeping every repeated ID. Do not average per-prompt
instruction accuracies. For `[[True, True, True], [False]]`, the prompt metric
is 0.5 and the instruction metric is 0.75. The caller preserves the raw prompt
and kwargs and forwards `final_text[0]` without additional scorer-side trimming,
translation, reasoning-tag stripping or Markdown cleanup.

## Reproduction

Read-only audit revision:
`Hugging-Face-KREW/k-llm-eval-sprint@da7053db1d4858239856695a2cfed702173234b6`,
`teams/team-c-ifeval-ko/evidence/checker-audit/`.
Original Ko revision: `54199e3801116897697babf341865741dcd06fc8`.
The verifier checks all `SHA256SUMS` entries, source hashes, dependency versions
and NLTK resource hashes before evaluation. Audit inputs and expected results
are read-only.

Run commands from the Lighteval repository root. If the audit inputs, pinned
sources and dependencies are already available, activate the appropriate Python
environment and supply your own directories. The registered-task verifier needs
an installed Lighteval environment, including its declared optional Ko packages:

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -e . 'langdetect==1.0.9' 'immutabledict==4.3.1' \
  'packaging==26.3' 'pyarrow==26.0.0'
```

On WSL, use a Linux-filesystem virtual environment. A CPU build of PyTorch is
sufficient; neither verifier generates model responses.

Run the direct scorer regression using the ported checkers:

```bash
KO_AUDIT=/path/to/checker-audit
KO_SOURCES=/path/to/restored-audit-sources
PYTHONDONTWRITEBYTECODE=1 python3 tests/ifeval_ko/verify_scoring.py \
  --audit-dir "$KO_AUDIT" --source-root "$KO_SOURCES" \
  --checker-mode ported \
  --output results/ifeval_ko/scoring-parity-ported.json
PYTHONDONTWRITEBYTECODE=1 python3 "$KO_AUDIT/test_audit.py"
python3 tests/unit/tasks/test_ifeval_ko_scoring.py
```

Run the real registered task with the same fixtures:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tests/ifeval_ko/verify_registered_task.py \
  --audit-dir "$KO_AUDIT" --source-root "$KO_SOURCES" \
  --output results/ifeval_ko/registered-task-results.json
```

This independently executes the original Ko evaluator, direct ported scorer,
registered formatter/metric, corpus aggregations and 342-item dataset Doc
conversion. It does not require anyone else's saved results. It records the
actual Git HEAD and hashes of the loaded task sources and verifier.

Optionally compare previously saved direct and registered results as well:

```bash
KO_UPSTREAM_RESULTS=/path/to/registered-task-results.json
PYTHONDONTWRITEBYTECODE=1 python3 tests/ifeval_ko/verify_registered_task.py \
  --audit-dir "$KO_AUDIT" --source-root "$KO_SOURCES" \
  --direct-results results/ifeval_ko/scoring-parity-ported.json \
  --upstream-results "$KO_UPSTREAM_RESULTS" \
  --output results/ifeval_ko/registered-task-comparison.json
```

Saved results must contain per-case decisions, ordered IDs, keys and input/response
hashes, plus the supplemental cases. The registered verifier refuses to overwrite
an existing output; choose new output names when preserving previous reports.

`--audit-dir` identifies the pinned `checker-audit/` evidence directory.
`--source-root` identifies the directory containing `sources/` and
`.cache/nltk_data/`. These may be different directories.

For a fresh environment, set the path to your documentation repository checkout
and export the pinned audit into a separate validation directory. The pinned
commit must be available in that checkout. Setup requires network access:

```bash
KO_DOCS_REPO=/path/to/k-llm-eval-sprint
KO_AUDIT=$(mktemp -d)
git -C "$KO_DOCS_REPO" archive da7053db1d4858239856695a2cfed702173234b6 \
  teams/team-c-ifeval-ko/evidence/checker-audit/ \
  | tar -x -C "$KO_AUDIT" --strip-components=4
python3 -m venv "$KO_AUDIT/.venv"
"$KO_AUDIT/.venv/bin/pip" install -r "$KO_AUDIT/requirements.lock.txt"
"$KO_AUDIT/.venv/bin/python" "$KO_AUDIT/fetch_sources.py"
"$KO_AUDIT/.venv/bin/python" -c \
  'import nltk, sys; assert nltk.download("punkt_tab", download_dir=sys.argv[1], quiet=True)' \
  "$KO_AUDIT/.cache/nltk_data"
PYTHONDONTWRITEBYTECODE=1 "$KO_AUDIT/.venv/bin/python" tests/ifeval_ko/verify_scoring.py \
  --audit-dir "$KO_AUDIT" --source-root "$KO_AUDIT" --checker-mode ported
```

The existing baseline `test_audit.py` validates the reference evidence, including
negative controls. It does not execute the new scorer. `verify_scoring.py`
separately invokes `score_response` on all 156 full cases, matching by `case_id`.
It uses `ko_eval_all_kwargs` when present and otherwise `ko_all_kwargs`.
Each case is seeded with Python `random.seed(0)`; `DetectorFactory.seed=0`;
one worker is used. The verifier also compares actual candidate order, checker
creation/build/call traces and input immutability against the archived reference.
Supplementary strict and loose entry points are each checked, including when
strict raises; the combined entry's exception propagation is checked separately.

## Environment and result artifact

Validated with Python 3.12.3; nltk 3.10.3; langdetect 1.0.9; immutabledict 4.3.1;
packaging 26.3; pyarrow 26.0.0. The registered-task run used CPU PyTorch
2.14.1+cpu, transformers 5.19.0 and inspect-ai 0.3.280 in a separate Linux
environment. The result records its package versions. Numeric-text language detection logs from `123`
are emitted by the original checker, which internally catches the exception
and returns True; these are not unhandled scoring failures.

`scoring-parity-ported.json` and `registered-task-results.json` contain the actual
command/environment, source/evidence/verifier hashes, each case's flags, metric
counts, auxiliary outcomes and mismatch list. They are local artifacts ignored by
the repository's existing `*.json` rule. Keep these reports as PR attachments
rather than committing machine-specific runtime paths. On failure, the report includes
the first mismatch's original input and old/new judgments; instruction-level
differences include `key`, `instruction_index`, and `instruction_id`.
