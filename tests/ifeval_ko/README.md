# IFEval-Ko scoring

`src/lighteval/tasks/tasks/ifeval_ko/scoring.py` provides the independent Ko
strict/loose scorer. **Direct scorer regression passes all 156 fixed-response
cases**, matching the predeclared expectations, stored original Ko results and
a live run of the pinned original evaluator.

## Current validation status

- Main regression: **156/156 cases**, strict **247/247 instructions + 156/156 prompts**,
  loose **247/247 instructions + 156/156 prompts**. Missing cases, unexpected
  scoring errors, decision differences and call-trace differences: **0**.
- Auxiliary inputs: **18/18**, each mode **10 normal returns + 8 expected exceptions**.
  These are excluded from the main metric denominators. Expected exceptions are
  contract checks, not successful normal scores.
- Policy/verifier tests: **11 passed**. Reference audit tests: **25 passed**.
- Ruff check and format check pass with Ruff `0.11.10`.

| Metric | Original Ko | New scorer | Value (both) | Absolute error |
| --- | --- | --- | --- | --- |
| `prompt_level_strict_acc` | 71/156 | 71/156 | 0.4551282051282051 | 0 |
| `inst_level_strict_acc` | 133/247 | 133/247 | 0.5384615384615384 | 0 |
| `prompt_level_loose_acc` | 79/156 | 79/156 | 0.5064102564102564 | 0 |
| `inst_level_loose_acc` | 142/247 | 142/247 | 0.5748987854251012 | 0 |

The Ko checker ports and `main.py` are not included yet. Validation uses the
unmodified pinned Ko registry in a validation-only package namespace; production
code imports the Ko registry from its own package. The reference is imported in
the audit's `isolated-source` mode, retaining its original imports and source
bytes; the archived reference run used `full-package`.

**Registered-task/Doc/metric-grouping validation and `lighteval tasks inspect`
remain pending integration.** English/French runtime regression, 23-item model
integration and the full 342-item split have not been run.

## Validation after integration

Once the team's `instructions.py`, `instructions_registry.py`,
`instructions_util.py` and `main.py` are integrated into the shared implementation
branch, validation will proceed as follows:

1. Run the direct scorer regression with `--checker-mode ported` to verify all
   156 fixed-response cases and the 18 auxiliary inputs using the ported checkers.
2. Repeat the fixed-response regression through the registered Ko task's Doc
   conversion and metric computation. Require strict and loose agreement on all
   247 instruction decisions and 156 prompt decisions per mode, identical metric
   numerators/denominators, absolute metric error at most `1e-12`, and no missing
   cases or unexpected scoring errors.
3. Run `lighteval tasks inspect` and compare its output with the original prompts,
   instruction order and kwargs, including repeated instruction IDs. Attach the
   inspection output and integration regression results to the Draft PR.
4. Mark the PR ready for review after these checks pass. Report direct scorer
   validation and registered-task validation separately so the evidence identifies
   which execution path was tested.

The 23-item model integration and full 342-item evaluation remain subsequent
stages; they are not covered by the fixed-response regression.

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
sources and dependencies are already available, activate that Python environment
and supply your own directories:

```bash
KO_AUDIT=/path/to/checker-audit
KO_SOURCES=/path/to/restored-audit-sources
PYTHONDONTWRITEBYTECODE=1 python3 tests/ifeval_ko/verify_scoring.py \
  --audit-dir "$KO_AUDIT" --source-root "$KO_SOURCES" \
  --checker-mode pinned-source \
  --output results/ifeval_ko/scoring-parity.json
PYTHONDONTWRITEBYTECODE=1 python3 "$KO_AUDIT/test_audit.py"
python3 tests/unit/tasks/test_ifeval_ko_scoring.py
```

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
  --audit-dir "$KO_AUDIT" --source-root "$KO_AUDIT" --checker-mode pinned-source
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

Python 3.12.3; nltk 3.10.3; langdetect 1.0.9; immutabledict 4.3.1;
packaging 26.3; pyarrow 26.0.0. Numeric-text language detection logs from `123`
are emitted by the original checker, which internally catches the exception
and returns True; these are not unhandled scoring failures.

`results/ifeval_ko/scoring-parity.json` contains the actual command/environment,
source/evidence/scorer/verifier hashes, each case's flags, metric counts,
auxiliary outcomes and mismatch list. It is a local artifact ignored by the
repository's existing `*.json` rule. On failure, the report and console include
the first mismatch's original input and old/new judgments; instruction-level
differences include `key`, `instruction_index`, and `instruction_id`.
