import unittest

from crn_models import ReactionNetwork
from parser_utils import (
    ReactionFileParser,
    ReactionParseError,
    parse_reaction_file,
    parse_reaction_text,
)


class ReactionParserTests(unittest.TestCase):
    def test_object_api_returns_domain_model(self):
        network = ReactionFileParser().parse_file("Example_Data/crn1.react")
        self.assertIsInstance(network, ReactionNetwork)
        self.assertEqual(network.reactions[0].source_complex, 0)
        self.assertEqual(network.reaction_graph.edges[0].weight, 1.0)

    def test_example_file(self):
        result = parse_reaction_file("Example_Data/crn1.react")
        self.assertEqual(len(result["reactions"]), 6)
        self.assertEqual(len(result["complexes"]), 11)
        self.assertEqual(result["complexes"][0]["label"], "2 X + 3 Y")
        self.assertEqual(result["complex_index"]["0"], 8)
        self.assertEqual(result["reactions"][0]["rate"], 1.0)
        self.assertEqual(result["reactions"][5]["reactants"], {"A": 1, "B": 1})
        self.assertEqual(result["reactions"][5]["reactant_coefficient_symbols"], {"A": "a", "B": "b"})
        for reaction in result["reactions"]:
            source, target = reaction["source_complex"], reaction["target_complex"]
            self.assertEqual(result["adjacency_matrix"][source][target], 1)
            self.assertEqual(result["adjacency_matrix"][target][source], 1)

    def test_repeated_complex_uses_one_index(self):
        text = """Reactions:
        A k1-> B
        B k2-> A
        Rate Constants:
        k1 = 2
        k2 = 3
        """
        result = parse_reaction_text(text)
        self.assertEqual(len(result["complexes"]), 2)
        self.assertEqual(result["adjacency_matrix"], [[0, 1], [1, 0]])
        self.assertEqual([edge["weight"] for edge in result["reaction_graph"]["edges"]], [2.0, 3.0])

    def test_undefined_rate_is_an_error(self):
        with self.assertRaisesRegex(ReactionParseError, "Undefined rate constant"):
            parse_reaction_text("Reactions:\nA k1-> B", unresolved="error")

    def test_missing_values_are_symbolic_by_default(self):
        result = parse_reaction_text("Reactions:\na A k1-> B")
        self.assertEqual(result["reactions"][0]["reactants"], {"A": "a"})
        self.assertIsNone(result["reactions"][0]["rate"])
        self.assertEqual(result["reaction_graph"]["edges"][0]["weight"], "k1")
        self.assertEqual(result["complex_index"], {"a A": 0, "B": 1})

    def test_missing_values_can_be_set_to_one(self):
        result = parse_reaction_text("Reactions:\na A k1-> B", unresolved="one")
        self.assertEqual(result["reactions"][0]["reactants"], {"A": 1})
        self.assertEqual(result["reactions"][0]["rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
