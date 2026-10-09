import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from importlib.util import find_spec

from crntanalysis.orchestrator import (
    AnalysisReportReader,
    AnalysisReportWriter,
    CRNAnalysisService,
    main,
)


REACTION_TEXT = """Reactions:
A k1-> B
Rate Constants:
k1 = 2
"""


class OrchestratorTests(unittest.TestCase):
    def test_raw_standard_ode_text_is_detected_automatically(self):
        outcome = CRNAnalysisService().analyze_text("param k=2\nx'=-k*x\ndone")
        self.assertEqual(outcome.input_format, "ode")
        self.assertEqual(outcome.network.rate_constants, {"k": 2})

    def test_cli_enables_reciprocal_and_fractional_realization(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            status = main([
                "--file", "Example_Data/AFmodel.ode", "--allow-fractional",
                "--lift-rational", "--no-file",
            ])
        self.assertEqual(status, 0)
        self.assertIn("augmented network", stdout.getvalue())
        self.assertIn("deficiency = 6", stdout.getvalue())

    def test_additional_bundled_examples_are_valid(self):
        examples = [
            "Example_Data/reversible_conversion.react",
            "Example_Data/enzyme_binding.react",
            "Example_Data/reversible_conversion.ode",
            "Example_Data/linear_pathway.ode",
        ]
        for path in examples:
            with self.subTest(path=path):
                outcome = CRNAnalysisService().analyze_file(path)
                self.assertGreater(len(outcome.network.reactions), 0)
                self.assertGreater(outcome.deficiency.number_of_complexes, 0)

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

    def test_writer_creates_plain_text_summary(self):
        outcome = CRNAnalysisService().analyze_text(REACTION_TEXT)
        with tempfile.TemporaryDirectory() as directory:
            path = AnalysisReportWriter().write(outcome, directory, extension="txt")
            self.assertEqual(path.suffix, ".txt")
            self.assertIn("Chemical Reaction Network Deficiency Analysis", path.read_text())
            self.assertIn("deficiency = 0", path.read_text())

    def test_reader_restores_structured_report_for_visualization(self):
        outcome = CRNAnalysisService().analyze_text(REACTION_TEXT)
        with tempfile.TemporaryDirectory() as directory:
            path = AnalysisReportWriter().write(outcome, directory, extension="output")
            restored = AnalysisReportReader().read(path)
            self.assertEqual(restored.to_dict(), outcome.to_dict())

    def test_reader_rejects_plain_text_and_invalid_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            text_path = Path(directory) / "report.txt"
            text_path.write_text("summary")
            with self.assertRaisesRegex(ValueError, "structured"):
                AnalysisReportReader().read(text_path)
            invalid_path = Path(directory) / "broken.analysis"
            invalid_path.write_text("not json")
            with self.assertRaisesRegex(ValueError, "Invalid analysis report"):
                AnalysisReportReader().read(invalid_path)

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
