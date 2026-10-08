import tempfile
import unittest
from pathlib import Path

from crntanalysis.deficiency_utils import calculate_deficiency
from crntanalysis.orchestrator import CRNAnalysisService, AnalysisReportReader, AnalysisReportWriter
from crntanalysis.reaction_parser import ReactionFileParser, ReactionParseError


class GeneralizedKineticsTests(unittest.TestCase):
    def test_kinetic_orders_are_separate_from_stoichiometry(self):
        network = ReactionFileParser().parse_text(
            "Reactions:\nY k-> 0\nRate Constants:\nk = 2\nKinetic Orders:\nk = 1.4 Y"
        )
        reaction = network.reactions[0]
        self.assertEqual(network.reactant_complex(reaction).species, {"Y": 1})
        self.assertEqual(reaction.kinetic_orders, {"Y": 1.4})
        self.assertEqual(reaction.rate_expression, "k*Y**1.4")
        self.assertEqual(calculate_deficiency(network).deficiency, 0)

    def test_rational_rate_law_preserves_stoichiometric_deficiency(self):
        network = ReactionFileParser().parse_text(
            "Reactions:\nX + Y k-> Y\nRate Constants:\nk = 1\na = 3\nz = 4\nRate Laws:\nk = k*X*Y/(1+X+a*z)"
        )
        self.assertIn("/(X + a*z + 1)", network.reactions[0].rate_expression)
        self.assertEqual(network.reactions[0].weight, 1)
        self.assertEqual(calculate_deficiency(network).stoichiometric_rank, 1)

    def test_kinetic_declarations_reject_ambiguity_unknown_labels_and_executable_code(self):
        prefix = "Reactions:\nY k-> 0\n"
        for suffix in ("Rate Laws:\nmissing = Y", "Rate Laws:\nk = f(Y)",
                       "Rate Laws:\nk = Y\nKinetic Orders:\nk = 1.4 Y"):
            with self.subTest(suffix=suffix), self.assertRaises(ReactionParseError):
                ReactionFileParser().parse_text(prefix + suffix)

    def test_augmented_analysis_report_round_trip_preserves_constraints_and_rates(self):
        outcome = CRNAnalysisService().analyze_file(
            "Example_Data/AFmodel.ode", allow_fractional=True, lift_rational=True
        )
        with tempfile.TemporaryDirectory() as directory:
            path = AnalysisReportWriter().write(outcome, directory)
            restored = AnalysisReportReader().read(path)
            self.assertEqual(restored.to_dict(), outcome.to_dict())
        self.assertEqual(outcome.network.analysis_metadata["deficiency_scope"], "augmented_realization")

