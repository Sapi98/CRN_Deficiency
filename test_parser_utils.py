import unittest

from parser_utils import ReactionParseError, parse_reaction_file, parse_reaction_text


class ReactionParserTests(unittest.TestCase):
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
            parse_reaction_text("Reactions:\nA k1-> B")


if __name__ == "__main__":
    unittest.main()
