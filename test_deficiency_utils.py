import unittest

from crntanalysis.crn_models import Complex, Reaction, ReactionGraph, ReactionNetwork
from crntanalysis.deficiency_utils import DeficiencyCalculator, DeficiencyError, calculate_deficiency
from crntanalysis.reaction_parser import ReactionFileParser


def network_from(complexes, reactions):
    return ReactionNetwork(
        reactions=reactions,
        complexes=complexes,
        reaction_graph=ReactionGraph(complexes, reactions),
        adjacency_matrix=[],
        rate_constants={},
        stoichiometric_coefficients={},
        initial_conditions={},
    )


class DeficiencyCalculatorTests(unittest.TestCase):
    def test_example_reaction_network(self):
        network = ReactionFileParser().parse_file("Example_Data/crn1.react")
        result = calculate_deficiency(network)
        self.assertEqual((result.number_of_complexes, result.stoichiometric_rank), (11, 4))
        self.assertEqual((result.number_of_linkage_classes, result.deficiency), (5, 2))
        self.assertEqual(
            [item.deficiency for item in result.linkage_classes], [0, 0, 0, 1, 0]
        )
        self.assertEqual(result.linkage_classes[3].complex_indices, [6, 7, 8])

    def test_isolated_complex_is_a_linkage_class(self):
        complexes = [Complex(0, "A", {"A": 1}), Complex(1, "B", {"B": 1})]
        result = DeficiencyCalculator().calculate(network_from(complexes, []))
        self.assertEqual(result.number_of_linkage_classes, 2)
        self.assertEqual(result.deficiency, 0)
        self.assertEqual([item.deficiency for item in result.linkage_classes], [0, 0])

    def test_symbolic_rank_is_generic(self):
        complexes = [Complex(0, "a A", {"A": "a"}), Complex(1, "B", {"B": 1})]
        reactions = [Reaction(0, 0, 1, "k1")]
        result = calculate_deficiency(network_from(complexes, reactions))
        self.assertTrue(result.symbolic_rank)
        self.assertEqual((result.stoichiometric_rank, result.deficiency), (1, 0))

    def test_unknown_complex_is_rejected(self):
        network = network_from([Complex(0, "A", {"A": 1})], [Reaction(0, 0, 2, "k")])
        with self.assertRaisesRegex(DeficiencyError, "unknown target"):
            calculate_deficiency(network)


if __name__ == "__main__":
    unittest.main()
