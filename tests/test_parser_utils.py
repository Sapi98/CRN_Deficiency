import unittest
from pprint import pprint

from crntanalysis.crn_models import ReactionNetwork
from crntanalysis.reaction_parser import (
    ReactionFileParser,
    ReactionParseError,
    parse_reaction_file,
    parse_reaction_text,
)


class ReactionParserTests(unittest.TestCase):
    def test_object_api_returns_domain_model(self):
        network = ReactionFileParser().parse_file("Example_Data/crn1.react")
        print("\n=== Object API outcome ===")
        print(f"Network: {network!r}")
        print(f"First reaction source complex: {network.reactions[0].source_complex}")
        print(f"First graph edge weight: {network.reaction_graph.edges[0].weight}")
        self.assertIsInstance(network, ReactionNetwork)
        self.assertEqual(network.reactions[0].source_complex, 0)
        self.assertEqual(network.reaction_graph.edges[0].weight, 1.0)

    def test_example_file(self):
        result = parse_reaction_file("Example_Data/crn1.react")
        print("\n=== Example file outcome ===")
        pprint(result, sort_dicts=False)
        self.assertEqual(len(result["reactions"]), 6)
        self.assertEqual(len(result["complexes"]), 11)
        self.assertEqual(result["complexes"][0]["label"], "2 X + 3 Y")
        self.assertEqual(result["complex_index"]["0"], 8)
        self.assertEqual(result["reactions"][0]["rate"], 1.0)
        reaction = result["reactions"][5]
        self.assertEqual(
            result["complexes"][reaction["source_complex"]]["species"],
            {"A": 1, "B": 1},
        )
        for reaction in result["reactions"]:
            source, target = reaction["source_complex"], reaction["target_complex"]
            self.assertNotEqual(result["adjacency_matrix"][source][target], 0)
            self.assertEqual(
                result["adjacency_matrix"][source][target],
                result["adjacency_matrix"][target][source],
            )

    def test_repeated_complex_uses_one_index(self):
        text = """Reactions:
        A k1-> B
        B k2-> A
        Rate Constants:
        k1 = 2
        k2 = 3
        """
        result = parse_reaction_text(text)
        print("\n=== Repeated complex outcome ===")
        pprint(result, sort_dicts=False)
        self.assertEqual(len(result["complexes"]), 2)
        self.assertEqual(result["adjacency_matrix"], [[0, [2.0, 3.0]], [[2.0, 3.0], 0]])
        self.assertEqual([reaction["weight"] for reaction in result["reactions"]], [2.0, 3.0])

    def test_undefined_rate_is_an_error(self):
        with self.assertRaisesRegex(ReactionParseError, "Undefined rate constant"):
            parse_reaction_text("Reactions:\nA k1-> B", unresolved="error")

    def test_invalid_assignment_uses_reaction_error(self):
        with self.assertRaises(ReactionParseError):
            parse_reaction_text("Reactions:\nA k1-> B\nRate Constants:\nk1 = nope")

    def test_missing_values_are_symbolic_by_default(self):
        result = parse_reaction_text("Reactions:\na A k1-> B")
        print("\n=== Symbolic missing values outcome ===")
        pprint(result, sort_dicts=False)
        source = result["reactions"][0]["source_complex"]
        self.assertEqual(result["complexes"][source]["species"], {"A": "a"})
        self.assertIsNone(result["reactions"][0]["rate"])
        self.assertEqual(result["reactions"][0]["weight"], "k1")
        self.assertEqual(result["adjacency_matrix"], [[0, "k1"], ["k1", 0]])
        self.assertEqual(result["complex_index"], {"a A": 0, "B": 1})

    def test_missing_values_can_be_set_to_one(self):
        result = parse_reaction_text("Reactions:\na A k1-> B", unresolved="one")
        print("\n=== Default-one missing values outcome ===")
        pprint(result, sort_dicts=False)
        source = result["reactions"][0]["source_complex"]
        self.assertEqual(result["complexes"][source]["species"], {"A": 1})
        self.assertEqual(result["reactions"][0]["rate"], 1.0)

    def test_mixed_parallel_weights_and_zero_rate_validation(self):
        result = parse_reaction_text(
            "Reactions:\nA k1-> B\nB k2-> A\nRate Constants:\nk1 = 2"
        )
        self.assertEqual(result["adjacency_matrix"], [[0, [2.0, "k2"]], [[2.0, "k2"], 0]])
        with self.assertRaisesRegex(ReactionParseError, "must be positive"):
            parse_reaction_text("Reactions:\nA k1-> B\nRate Constants:\nk1 = 0")


if __name__ == "__main__":
    unittest.main()
