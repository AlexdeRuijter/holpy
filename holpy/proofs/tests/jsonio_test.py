from __future__ import annotations

import json
import os
import tempfile
import unittest

from holpy.proofs.jsonio import dumps_theory, write_theory


class JsonioTest(unittest.TestCase):
    def test_sorted_keys(self):
        d = {"z": 1, "a": {"b": 2, "a": 3}}
        s = dumps_theory(d)
        self.assertIn('"a":', s)
        self.assertIn('"z":', s)
        # Keys sorted at every level
        self.assertTrue(s.index('"a"') < s.index('"z"'))

    def test_separators(self):
        d = {"a": 1, "b": 2}
        s = dumps_theory(d)
        self.assertIn(": ", s)
        # No "," without space between key-value pairs inside objects
        # (except when array elements are separated by commas before newline)
        # Just verify basic separator presence.
        self.assertIn(", ", s)

    def test_non_ascii_kept(self):
        d = {"th": "⊢ ∀x. x = x"}
        s = dumps_theory(d)
        self.assertIn("⊢", s)
        self.assertNotIn("\\u", s)

    def test_one_entry_per_line_for_content_and_proof(self):
        with open("holpy/library/logic.json", encoding="utf-8") as f:
            d = json.load(f)
        s = dumps_theory(d)
        # Each content item is on its own line (starts with 4-space indent and {)
        content_lines = [line for line in s.splitlines() if line.startswith("    {")]
        # There should be exactly as many as content items
        self.assertEqual(len(content_lines), len(d["content"]))
        # Each proof entry should start with indented {
        proof_lines = [line for line in s.splitlines() if '"rule"' in line]
        # Just check that proof items appear.
        self.assertGreater(len(proof_lines), 0)

    def test_no_trailing_whitespace(self):
        d = {"a": [1, 2]}
        s = dumps_theory(d)
        for line in s.splitlines():
            self.assertEqual(line, line.rstrip())

    def test_final_newline_exactly_one(self):
        d = {"a": 1}
        s = dumps_theory(d)
        self.assertTrue(s.endswith("\n"))
        self.assertFalse(s.endswith("\n\n"))

    def test_idempotence(self):
        with open("holpy/library/nat.json", encoding="utf-8") as f:
            d = json.load(f)
        s1 = dumps_theory(d)
        s2 = dumps_theory(json.loads(s1))
        self.assertEqual(s1, s2)

    def test_write_theory_read_back(self):
        with open("holpy/library/logic.json", encoding="utf-8") as f:
            d = json.load(f)
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w", newline="\n"
        ) as tmp:
            path = tmp.name
        try:
            write_theory(path, d)
            with open(path, encoding="utf-8", newline="\n") as f:
                s = f.read()
            self.assertEqual(json.loads(s), d)
            # Check newline is \n
            self.assertIn("\n", s)
            self.assertNotIn("\r\n", s)
        finally:
            os.unlink(path)

    def test_smaller_than_indent4(self):
        with open("holpy/library/logic.json", encoding="utf-8") as f:
            d = json.load(f)
        s = dumps_theory(d)
        s4 = json.dumps(d, indent=4, separators=(", ", ": "), ensure_ascii=False, sort_keys=True)
        self.assertLess(len(s), len(s4))


if __name__ == "__main__":
    unittest.main()
