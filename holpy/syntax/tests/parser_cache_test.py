"""Tests that the Lark grammar cache does not change parsing results."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from lark import Lark

from holpy.logic import basic, context
from holpy.syntax import parser


class ParserCacheTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.uncached = {
            start: Lark(
                parser.grammar,
                start=start,
                parser="lalr",
                transformer=parser.HOLTransformer(),
                cache=False,
            )
            for start in ("type", "term", "thm")
        }

    def setUp(self) -> None:
        # ``list`` imports ``logic`` and provides the type constructors used
        # by both the type and the term samples below.
        basic.load_theory("list")
        context.set_context(
            "list",
            vars={
                "A": "bool",
                "B": "bool",
                "C": "bool",
                "P": "'a => bool",
                "Q": "'a => bool",
                "a": "'a",
                "b": "'a",
            },
        )

    def assert_same_results(self, start: str, parse, samples: list[str]) -> None:
        """Check that *parse* gives the same result with and without the cache."""
        for text in samples:
            with mock.patch.object(parser, f"{start}_parser", self.uncached[start]):
                without_cache = parse(text)
            with_cache = parse(text)
            self.assertEqual(without_cache, with_cache, text)

    def test_parse_type_with_and_without_cache(self) -> None:
        self.assert_same_results(
            "type",
            parser.parse_type,
            ["'a", "?'a", "nat", "'a list", "'a => 'b list", "('a => 'b) => 'c"],
        )

    def test_parse_term_with_and_without_cache(self) -> None:
        self.assert_same_results(
            "term",
            parser.parse_term,
            [
                "A & B --> C",
                "~A | B = C",
                "!x::'a. P x",
                "?x. P x & Q x",
                "%x::'a. x",
                "(P a) = (P b)",
            ],
        )

    def test_parse_thm_with_and_without_cache(self) -> None:
        self.assert_same_results(
            "thm",
            parser.parse_thm,
            [
                "|- A",
                "A |- B",
                "A, B |- A & B",
                "|- !x::'a. P x --> P x",
                "A, B |- B --> A",
            ],
        )

    def test_cache_path_is_in_user_cache_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"HOLPY_USER_DIR": tmp}):
                path = parser._lark_cache("term")
            self.assertEqual(path, str(Path(tmp) / "cache" / "lark_syntax_term.lark"))
            self.assertTrue((Path(tmp) / "cache").is_dir())

    def test_cache_disabled_when_directory_cannot_be_created(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # A file where the cache directory should be makes mkdir fail.
            (Path(tmp) / "cache").write_text("", encoding="utf-8")
            with mock.patch.dict(os.environ, {"HOLPY_USER_DIR": tmp}):
                self.assertFalse(parser._lark_cache("term"))


if __name__ == "__main__":
    unittest.main()
