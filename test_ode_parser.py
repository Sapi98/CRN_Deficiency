import unittest

from crntanalysis.crn_models import ReactionNetwork
from crntanalysis.ode_parser import ODEFileParser, ODEParseError, parse_ode_text


VALID_ODE = """ODE Model:
dx/dt = 2 * k1 * X^2 * Y - k2 * X
dy/dt = -k1 * X^2 * Y
Coefficients:
k1 = 0.5
k2 = 0.1
"""


class ODEParserTests(unittest.TestCase):
    def test_builds_canonical_reactions(self):
        result = parse_ode_text(VALID_ODE)
        self.assertEqual(len(result["reactions"]), 2)
        reaction = result["reactions"][0]
        self.assertEqual(result["complexes"][reaction["source_complex"]]["species"], {"X": 2, "Y": 1})
        self.assertEqual(result["complexes"][reaction["target_complex"]]["species"], {"X": 4})
        self.assertEqual(result["reactions"][0]["rate"], 0.5)
        self.assertEqual(result["adjacency_matrix"][0][1], 0.5)

    def test_object_api(self):
        parsed = ODEFileParser().parse_text(VALID_ODE)
        self.assertIsInstance(parsed.network, ReactionNetwork)
        self.assertEqual(parsed.equations[0].species, "X")

    def test_symbolic_missing_rate(self):
        result = parse_ode_text("ODE Model:\ndx/dt = k * X")
        self.assertIsNone(result["reactions"][0]["rate"])
        self.assertEqual(result["reactions"][0]["weight"], "k")
        self.assertEqual(result["adjacency_matrix"], [[0, "k"], ["k", 0]])

    def test_rejects_non_mass_action_ode_in_example(self):
        with self.assertRaisesRegex(ODEParseError, "consumes 'X'"):
            ODEFileParser().parse_file("Example_Data/crn2.ode")

    def test_invalid_assignment_uses_ode_error(self):
        with self.assertRaises(ODEParseError):
            parse_ode_text("ODE Model:\ndx/dt = k * X\nCoefficients:\nk = nope")

    def test_warns_about_unused_coefficient(self):
        result = parse_ode_text(VALID_ODE + "unused = 4\n")
        self.assertEqual(result["warnings"], ["Coefficient 'unused' is defined but not used"])


if __name__ == "__main__":
    unittest.main()
