import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from crntanalysis.orchestrator import AnalysisReportWriter, CRNAnalysisService, main


REACTION_TEXT = """Reactions:
A k1-> B
Rate Constants:
k1 = 2
"""


class OrchestratorTests(unittest.TestCase):
    def test_service_analyzes_text_without_console(self):
        outcome = CRNAnalysisService().analyze_text(REACTION_TEXT)
        self.assertEqual(outcome.input_format, "react")
        self.assertEqual(outcome.deficiency.deficiency, 0)

    def test_service_detects_file_format(self):
        outcome = CRNAnalysisService().analyze_file("Example_Data/crn1.react")
        self.assertEqual(outcome.input_format, "react")
        self.assertEqual(outcome.deficiency.deficiency, 2)

    def test_writer_creates_structured_analysis_file(self):
        outcome = CRNAnalysisService().analyze_text(REACTION_TEXT)
        with tempfile.TemporaryDirectory() as directory:
            path = AnalysisReportWriter().write(outcome, directory)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(path.suffix, ".analysis")
            self.assertEqual(payload["deficiency"]["deficiency"], 0)

    def test_cli_prints_and_writes_output_extension(self):
        with tempfile.TemporaryDirectory() as directory:
            stdout = StringIO()
            with redirect_stdout(stdout):
                status = main(
                    [
                        "--text",
                        REACTION_TEXT,
                        "--output-dir",
                        directory,
                        "--extension",
                        "output",
                    ]
                )
            self.assertEqual(status, 0)
            self.assertIn("deficiency = 0", stdout.getvalue())
            self.assertTrue((Path(directory) / "network_analysis.output").exists())


if __name__ == "__main__":
    unittest.main()
