# IFEval-Ko: selected 23-prompt response generation

Generate and save one Qwen response per selected prompt so the team can pass
the same saved responses to the original Ko evaluator and registered Lighteval
task. This stage runs Transformers generation only. It does not invoke either
scorer or establish model-response scoring parity.

## Recorded run

| Item | Value |
| --- | --- |
| Model and tokenizer | `Qwen/Qwen2.5-1.5B-Instruct` |
| Model/tokenizer revision | `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` |
| Dataset | `allganize/IFEval-Ko`, `default` / `train` |
| Dataset revision | `54199e3801116897697babf341865741dcd06fc8` |
| Selection | 23 prompts, 40 instruction occurrences |
| Backend | Transformers `AutoModelForCausalLM.generate` |
| Device and requested dtype | Apple MPS, float16 |
| Batch size / responses per prompt | 1 / 1 |
| Few-shot examples | 0 |
| Sampling / temperature | `do_sample=False` / `temperature=0.0` |
| Output limit | 1,280 new tokens per prompt |
| Declared stop strings | `<end_of_turn>`, `<\|im_end\|>` |
| Seed | 0 |
| Generated / generation errors / unattempted | 23 / 0 / 0 |
| Empty responses | 0 |
| Token-limit termination | key `1127` |
| Total script runtime | approximately 185.6 seconds |
| Responses scored | 0 |

The complete generation configuration, including inherited model settings and
EOS/pad IDs, actual dtype, environment versions, execution timestamps and Git
revision are recorded in `manifest.json`. The official tokenizer chat template
is applied once; its rendered input and input token IDs are saved for each
prompt. No custom system message is supplied; any default system text comes
from the pinned tokenizer template.

The model's sampling defaults are explicitly overridden. Transformers may warn
that `temperature` and `top_k` are ignored because sampling is disabled.

Selected keys, in generation order:

```json
[3743, 136, 3518, 1233, 3445, 3442, 1262, 1082, 1127, 3710, 122,
 3563, 1107, 3073, 3311, 3750, 1203, 2142, 1268, 3538, 1928, 2035, 1800]
```

## Run from the repository root

Use the team's merged `team-c/ifeval-ko` code and an activated Python 3.11
environment with the required dependencies installed. The task merge commit is
`bc7bc0beaee028e0e2f16a734c36048c121609c6`; the actual run's code revision is in
the manifest, and an exact generator snapshot is included in the run artifacts.

The default selection path expects the operations repository next to the code
repository:

```text
Projects/
  k-llm-eval-sprint/
  lighteval-ifeval-ko/
```

```bash
python scripts/ifeval_ko/generate_responses.py \
  --output-dir outputs/ifeval_ko/qwen-23-001
```

On macOS, prefix the command with `caffeinate -i` to prevent idle sleep during
generation. An existing output directory is rejected; use a new name for another
run. The script checks the selection against the recorded 23 keys, 40
instruction occurrences, and 21 instruction types before loading the model.

## Saved artifacts and integrity

The run directory contains:

| File | Contents |
| --- | --- |
| `selection.json` | Copy of the selection file used by this run |
| `selected-samples.json` | Original selected rows, including ordered IDs and unmodified kwargs |
| `responses.jsonl` | One record per attempted prompt, with source fields, rendered input, input/output token IDs, raw decoded text, scoring response, termination reason and generation time or error |
| `manifest.json` | Revisions, actual generation settings, environment, stage counts and artifact hashes |
| `requirements.lock.txt` | Installed dependency versions, excluding editable packages |
| `generate_responses.py` | Exact script snapshot used by the run |
| `run.log` | Execution log |
| `SHA256SUMS` | SHA-256 checksums for the seven files above |

The saved run passed checksum verification for all seven files. Additional
checks confirmed 23 unique keys in the selected order, 23 generated responses,
40 instructions, unchanged original input fields, matching response hashes,
and identical `response` / `scoring_response` fields. There were no generation
errors, unattempted prompts or empty responses.

Run checksum verification from inside the extracted run directory:

```bash
shasum -a 256 -c SHA256SUMS
```

Preserve the original run directory. Package it as a PR attachment; the
repository ignores `outputs/` and JSON runtime artifacts. The generator and
this README are source changes that can be committed separately.

To reproduce generation in a fresh checkout and Python 3.11 environment, point
`KO_RUN_DIR` at the extracted original run directory:

```bash
python -m pip install -e . -r "$KO_RUN_DIR/requirements.lock.txt"
python "$KO_RUN_DIR/generate_responses.py" \
  --selection "$KO_RUN_DIR/selection.json" \
  --output-dir outputs/ifeval_ko/qwen-23-reproduction-001
```

Run these commands from the Lighteval repository root. Reproduction requires an
MPS-capable Mac. File checksums verify saved artifacts; new runs have different
timestamps and logs, and cross-environment generation is not guaranteed to be
byte-identical.

## Response contract and remaining work

For both evaluators, use each generated record's `response` or equivalent
`scoring_response` verbatim, together with its original `key`, `prompt`,
`instruction_id_list` and `kwargs`. Special tokens and declared stop strings
are removed during response extraction. No whitespace stripping, NFC
normalization, Markdown cleanup, or reasoning removal is applied here. The
original generated token IDs and decoded text including special tokens are
preserved separately.

Token-limit termination is retained as a model response, not converted into a
generation error or removed from the sample. Key `1127` must remain in the
cross-evaluation input. A blank response, if generated in another run, is also
retained. Runtime exceptions are saved as errors and stop the run; they are not
replaced with blank successful responses.

The one-item hardware smoke test is separate from this 23-prompt run. The
remaining team work is to score these identical saved responses with both
evaluators, compare per-instruction/per-prompt strict and loose judgments and
all four aggregate metrics, and investigate mismatches. Model-response scoring
parity and full-split model evaluation are not claimed by this run.
