import tempfile
import unittest
from pathlib import Path
from importlib.util import find_spec

from crntanalysis.crn_models import Complex, Reaction
from test_deficiency_utils import network_from
from crntanalysis.visualization import NetworkGraphAdapter, NetworkVisualizer


@unittest.skipUnless(find_spec("networkx") and find_spec("matplotlib"), "optional visualization dependencies")
class VisualizationTests(unittest.TestCase):
    def setUp(self):
        self.network = network_from(
            [Complex(2, "A", {"A": 1}), Complex(5, "B", {"B": 1}), Complex(9, "C", {"C": 1})],
            [Reaction(0, 2, 5, "k1"), Reaction(1, 2, 5, "k2", 2.0),
             Reaction(2, 5, 2, "k3"), Reaction(3, 2, 2, "k4"), Reaction(4, 2, 2, "k5")])

    def test_adapter_preserves_identity_and_linkages(self):
        adapter = NetworkGraphAdapter()
        graph = adapter.reaction_graph(self.network)
        self.assertEqual(set(graph), {2, 5, 9})
        self.assertEqual(graph.number_of_edges(), 5)
        self.assertIs(graph[2][5][0]["reaction"], self.network.reactions[0])
        self.assertEqual(graph[2][5][0]["weight"], "k1")
        linkage = adapter.linkage_graph(self.network)
        self.assertEqual(len(linkage[2][5]["reactions"]), 3)
        self.assertEqual(linkage.degree(9), 0)

    def test_render_and_export(self):
        visualizer = NetworkVisualizer()
        figure, ax = visualizer.draw_reaction_network(self.network, show_deficiency=True)
        self.assertEqual(len(ax.patches), 5)
        self.assertTrue(any("k1" in text.get_text() for text in ax.texts))
        with tempfile.TemporaryDirectory() as directory:
            for extension in ("png", "svg", "pdf"):
                path = visualizer.save(figure, Path(directory) / f"network.{extension}")
                self.assertGreater(path.stat().st_size, 100)
        figure2, ax2 = visualizer.draw_linkage_graph(self.network, show_deficiency=True)
        self.assertEqual(len(ax2.patches), 2)
        self.assertEqual(len(ax2.get_legend().get_texts()), 2)

    def test_empty_and_invalid_networks(self):
        NetworkVisualizer().draw_linkage_graph(network_from([], []))
        self.network.reactions.append(Reaction(10, 2, 100, "bad"))
        with self.assertRaises(ValueError):
            NetworkGraphAdapter().reaction_graph(self.network)


if __name__ == "__main__":
    unittest.main()
