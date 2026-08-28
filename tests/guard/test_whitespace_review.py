import importlib.util
import sys
import unittest
from pathlib import Path


_MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "guard" / "whitespace_review.py"
_MODULE_SPEC = importlib.util.spec_from_file_location("whitespace_review", _MODULE_PATH)
assert _MODULE_SPEC and _MODULE_SPEC.loader
whitespace_review = importlib.util.module_from_spec(_MODULE_SPEC)
sys.modules[_MODULE_SPEC.name] = whitespace_review
_MODULE_SPEC.loader.exec_module(whitespace_review)

Issue = whitespace_review.Issue
evaluate_issues = whitespace_review.evaluate_issues
parse_git_check_output = whitespace_review.parse_git_check_output


class WhitespaceReviewTest(unittest.TestCase):
    def test_exact_allowlisted_markdown_issue_is_allowed(self):
        issue = Issue(
            path="docs/example.md",
            line=3,
            trailing_ws=2,
            body_sha256="body-hash",
            kind="markdown-hard-break",
        )
        allowed, unexpected = evaluate_issues(
            [issue],
            [
                {
                    "path": "docs/example.md",
                    "line": 3,
                    "trailing_ws": 2,
                    "body_sha256": "body-hash",
                    "kind": "markdown-hard-break",
                }
            ],
        )
        self.assertEqual(allowed, [issue])
        self.assertEqual(unexpected, [])

    def test_changed_body_is_not_allowed_by_line_number_alone(self):
        issue = Issue(
            path="docs/example.md",
            line=3,
            trailing_ws=2,
            body_sha256="changed-body",
            kind="markdown-hard-break",
        )
        allowed, unexpected = evaluate_issues(
            [issue],
            [
                {
                    "path": "docs/example.md",
                    "line": 3,
                    "trailing_ws": 2,
                    "body_sha256": "original-body",
                    "kind": "markdown-hard-break",
                }
            ],
        )
        self.assertEqual(allowed, [])
        self.assertEqual(unexpected, [issue])

    def test_unlisted_issue_is_unexpected(self):
        issue = Issue(
            path="docs/other.md",
            line=7,
            trailing_ws=2,
            body_sha256="body-hash",
            kind="markdown-hard-break",
        )
        allowed, unexpected = evaluate_issues(issue_list := [issue], [])
        self.assertEqual(allowed, [])
        self.assertEqual(unexpected, issue_list)

    def test_git_check_parser_keeps_only_diagnostics(self):
        output = (
            "docs/example.md:3: trailing whitespace.\n"
            "+text  \n"
            "docs/example.md:9: new blank line at EOF.\n"
        )
        issues = parse_git_check_output(output)
        self.assertEqual([(x.path, x.line) for x in issues], [("docs/example.md", 3)])


if __name__ == "__main__":
    unittest.main()
