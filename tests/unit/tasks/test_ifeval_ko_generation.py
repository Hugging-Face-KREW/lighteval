"""Generator compatibility and failure accounting tests without a model or MPS."""

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, sentinel


SCRIPT = Path(__file__).resolve().parents[3] / "scripts/ifeval_ko/generate_responses.py"


class Tokens:
    shape = (1, 1)

    def __getitem__(self, index):
        return self

    def tolist(self):
        return [2]


class Inputs(dict):
    def __init__(self):
        super().__init__(input_ids=Tokens())

    def to(self, device):
        return self


class GenerationTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("_test_ifeval_ko_generator", SCRIPT)
        self.generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.generator)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.selection = self.root / "selection.json"
        self.selection.write_text(json.dumps({"keys": self.generator.KEYS}), encoding="utf-8")
        self.run_index = 0
        self.rows = []
        instruction_index = 0
        for index, key in enumerate(self.generator.KEYS + list(range(100000, 100319))):
            count = 2 if index < 17 or 23 <= index < 145 else 1
            ids = [f"type-{i % 21}" for i in range(instruction_index, instruction_index + count)]
            self.rows.append(
                {"key": key, "prompt": f"Prompt {key}", "instruction_id_list": ids, "kwargs": [{}] * count}
            )
            instruction_index += count

    def run_generation(self, *, fail_generation_at=None, fail_log_at=None, legacy_loader=False):
        self.run_index += 1
        output = self.root / f"run-{self.run_index}"
        attempts = 0

        def generate(**kwargs):
            nonlocal attempts
            attempts += 1
            if attempts == fail_generation_at:
                raise RuntimeError("generation failed")
            return types.SimpleNamespace(sequences=Tokens())

        model = types.SimpleNamespace(
            generation_config=types.SimpleNamespace(eos_token_id=2, to_dict=lambda: {}),
            config=types.SimpleNamespace(max_position_embeddings=32768),
            parameters=lambda: iter([types.SimpleNamespace(dtype="torch.float16")]),
            generate=generate,
        )
        model.to = lambda device: model
        model.eval = lambda: model

        # The older loader accepts torch_dtype but has no dtype keyword.
        def load_legacy(model_id, *, revision, torch_dtype, trust_remote_code):
            self.assertIs(torch_dtype, sentinel.float16)
            return model

        load_model = Mock(side_effect=load_legacy) if legacy_loader else Mock(return_value=model)
        tokenizer = types.SimpleNamespace(
            chat_template="test template",
            eos_token_id=2,
            pad_token_id=0,
            apply_chat_template=lambda *args, **kwargs: "test input",
            decode=lambda *args, **kwargs: "test response",
        )
        tokenize = Mock(return_value=Inputs())
        tokenize.configure_mock(**vars(tokenizer))
        modules = {
            "torch": types.SimpleNamespace(
                backends=types.SimpleNamespace(mps=types.SimpleNamespace(is_available=lambda: True)),
                float16=sentinel.float16,
                mps=types.SimpleNamespace(synchronize=lambda: None),
                inference_mode=contextlib.nullcontext,
            ),
            "datasets": types.SimpleNamespace(load_dataset=lambda *args, **kwargs: self.rows),
            "transformers": types.SimpleNamespace(
                AutoModelForCausalLM=types.SimpleNamespace(from_pretrained=load_model),
                AutoTokenizer=types.SimpleNamespace(from_pretrained=lambda *args, **kwargs: tokenize),
                set_seed=lambda seed: None,
            ),
        }

        def log(*args, **kwargs):
            if attempts == fail_log_at and str(args[0]).startswith("  "):
                raise BrokenPipeError("success log failed")

        argv = [str(SCRIPT), "--selection", str(self.selection), "--output-dir", str(output)]
        previous_directory = Path.cwd()
        try:
            os.chdir(SCRIPT.parents[2])
            with (
                patch.dict(sys.modules, modules),
                patch.object(sys, "argv", argv),
                patch.object(self.generator, "command", return_value="0"),
                patch.object(self.generator, "version", return_value="test"),
                patch.object(self.generator, "print", side_effect=log, create=True),
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                code = self.generator.main()
        finally:
            os.chdir(previous_directory)
        manifest = json.loads((output / "manifest.json").read_text())
        path = output / "responses.jsonl"
        records = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
        return code, manifest, records

    def assert_accounting(self, manifest, records, expected):
        counts = tuple(manifest[name] for name in ("generated_count", "generation_error_count", "unattempted_count"))
        self.assertEqual(counts, expected)
        self.assertEqual(sum(counts), 23)
        self.assertTrue(all(count >= 0 for count in counts))
        self.assertEqual(manifest["generated_count"], sum(record["status"] == "generated" for record in records))
        self.assertEqual(manifest["generation_error_count"], sum(record["status"] == "error" for record in records))
        self.assertEqual(manifest["unattempted_count"], 23 - len(records))

    def test_success_with_legacy_loader_keyword(self):
        code, manifest, records = self.run_generation(legacy_loader=True)
        self.assertEqual(code, 0)
        self.assertEqual(manifest["status"], "responses_generated")
        self.assert_accounting(manifest, records, (23, 0, 0))

    def test_success_log_failure_counts_final_record_once(self):
        for index in (1, 23):
            with self.subTest(index=index):
                code, manifest, records = self.run_generation(fail_log_at=index)
                self.assertEqual(code, 1)
                self.assertEqual(manifest["error"]["type"], "BrokenPipeError")
                self.assertEqual(records[-1]["status"], "error")
                self.assert_accounting(manifest, records, (index - 1, 1, 23 - index))

    def test_generation_failure_preserves_completed_and_unattempted_counts(self):
        for index in (1, 7):
            with self.subTest(index=index):
                code, manifest, records = self.run_generation(fail_generation_at=index)
                self.assertEqual(code, 1)
                self.assertEqual(manifest["error"]["type"], "RuntimeError")
                self.assert_accounting(manifest, records, (index - 1, 1, 23 - index))


if __name__ == "__main__":
    unittest.main(verbosity=2)
