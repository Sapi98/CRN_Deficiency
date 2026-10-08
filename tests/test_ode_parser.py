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
    def test_equivalent_logistic_forms_have_identical_realizations(self):
        forms = ["x*(1-x/K)", "x-(1/K)*x^2", "x-(1/K)*x*x"]
        networks = [parse_ode_text(f"ODE Model:\ndx/dt = {rhs}") for rhs in forms]
        for result in networks[1:]:
            self.assertEqual(result["complexes"], networks[0]["complexes"])
            self.assertEqual(result["reactions"], networks[0]["reactions"])
        edges = networks[0]["reactions"]
        self.assertEqual({edge["weight"] for edge in edges}, {1.0, "1/K"})
        consuming = next(edge for edge in edges if edge["weight"] == "1/K")
        self.assertEqual(networks[0]["complexes"][consuming["source_complex"]]["species"], {"x": 2})
        self.assertEqual(networks[0]["complexes"][consuming["target_complex"]]["species"], {"x": 1})

    def test_effective_rates_and_implicit_unit_rate_resolve_in_strict_mode(self):
        result = parse_ode_text("ODE Model:\ndx/dt = x*(1-x/K)\nCoefficients:\nK = 8", unresolved="error")
        self.assertEqual({edge["rate"] for edge in result["reactions"]}, {1.0, 0.125})
        self.assertEqual(result["warnings"], [])

    def test_repeated_species_and_multiple_parameter_factors(self):
        result = parse_ode_text("ODE Model:\ndx/dt = -a*b*x*x\nCoefficients:\na = 2\nb = 3")
        edge = result["reactions"][0]
        self.assertEqual(edge["rate"], 6.0)
        self.assertEqual(result["complexes"][edge["source_complex"]]["species"], {"x": 2})

    def test_species_denominator_is_rejected_with_kinetic_explanation(self):
        with self.assertRaisesRegex(ODEParseError, "Species-dependent denominator"):
            parse_ode_text("ODE Model:\ndx/dt = x*(1-x/K)-x*y/(1+x+a*z)\ndy/dt = 0\ndz/dt = 0")

    def test_zero_equation_and_decimal_rate(self):
        result = parse_ode_text("ODE Model:\ndx/dt = 0.5*x\ndy/dt = 0")
        self.assertEqual(len(result["reactions"]), 1)
        self.assertEqual(result["reactions"][0]["rate"], 0.5)

    def test_function_calls_are_rejected_without_evaluation(self):
        with self.assertRaises(ODEParseError):
            parse_ode_text("ODE Model:\ndx/dt = __import__('os').getcwd()")

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
