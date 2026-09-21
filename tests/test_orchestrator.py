import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from importlib.util import find_spec

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

    def test_cli_reads_standard_input_and_can_suppress_outputs(self):
        stdout = StringIO()
        with patch("sys.stdin", StringIO(REACTION_TEXT)), redirect_stdout(stdout):
            status = main(["--stdin", "--format", "react", "--no-file", "--no-console"])
        self.assertEqual(status, 0)
        self.assertEqual(stdout.getvalue(), "")

    @unittest.skipUnless(
        find_spec("networkx") and find_spec("matplotlib"),
        "optional visualization dependencies",
    )
    def test_cli_writes_both_graphs_with_generated_names(self):
        with tempfile.TemporaryDirectory() as directory:
            stdout = StringIO()
            with redirect_stdout(stdout):
                status = main(
                    [
                        "--text", REACTION_TEXT,
                        "--format", "react",
                        "--output-dir", directory,
                        "--no-file", "--no-console",
                        "--reaction-graph", "--linkage-graph",
                        "--graph-format", "svg",
                        "--show-linkage-rates", "--show-linkage-deficiency",
                    ]
                )
            self.assertEqual(status, 0)
            self.assertTrue((Path(directory) / "network_analysis_reaction_graph.svg").exists())
            self.assertTrue((Path(directory) / "network_analysis_linkage_graph.svg").exists())
            self.assertEqual(stdout.getvalue().count("Graph file:"), 2)

    def test_cli_accepts_explicit_file_argument(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            status = main(["--file", "Example_Data/crn1.react", "--no-file"])
        self.assertEqual(status, 0)
        self.assertIn("deficiency = 2", stdout.getvalue())

    def test_output_name_is_shared_by_report_and_automatic_graph_paths(self):
        if not (find_spec("networkx") and find_spec("matplotlib")):
            self.skipTest("optional visualization dependencies")
        with tempfile.TemporaryDirectory() as directory:
            status = main(
                [
                    "--text", REACTION_TEXT,
                    "--output-dir", directory,
                    "--output-name", "experiment_01",
                    "--reaction-graph",
                    "--no-console",
                ]
            )
            self.assertEqual(status, 0)
            self.assertTrue((Path(directory) / "experiment_01.analysis").exists())
            self.assertTrue((Path(directory) / "experiment_01_reaction_graph.png").exists())


if __name__ == "__main__":
    unittest.main()
