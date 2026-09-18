"""Optional complex-graph visualization, independent of console and GUI code."""

from pathlib import Path

from crntanalysis.deficiency_utils import calculate_deficiency

__all__ = ["NetworkGraphAdapter", "NetworkVisualizer"]


def _networkx():
    """Load the optional graph dependency only when requested."""
    try:
        import networkx
    except ImportError as error:
        raise ImportError('Install visualization support: pip install "crntanalysis[visualization]"') from error
    return networkx


class NetworkGraphAdapter:
    """Convert domain objects without changing their indices or reaction identity."""

    def reaction_graph(self, network):
        """Return a MultiDiGraph; nodes reference complexes, edges reference reactions.

        Raises ValueError for duplicate indices or unknown reaction endpoints.
        """
        nx = _networkx()
        graph = nx.MultiDiGraph()
        for complex_ in network.complexes:
            if complex_.index in graph:
                raise ValueError("Complex indices must be unique")
            graph.add_node(complex_.index, label=complex_.label, complex=complex_)
        indices = set()
        for reaction in network.reactions:
            if reaction.index in indices:
                raise ValueError("Reaction indices must be unique")
            if reaction.source not in graph or reaction.target not in graph:
                raise ValueError("Reaction references an unknown complex")
            indices.add(reaction.index)
            graph.add_edge(reaction.source, reaction.target, key=reaction.index,
                           reaction=reaction, weight=reaction.weight)
        return graph

    def linkage_graph(self, network):
        """Return an undirected Graph, retaining all reactions on each connection."""
        nx = _networkx()
        directed = self.reaction_graph(network)
        graph = nx.Graph()
        graph.add_nodes_from(directed.nodes(data=True))
        for source, target, data in directed.edges(data=True):
            if not graph.has_edge(source, target):
                graph.add_edge(source, target, reactions=[])
            graph[source][target]["reactions"].append(data["reaction"])
        return graph


class NetworkVisualizer:
    """Render complex graphs; return Figure/Axes without opening a GUI window."""

    def __init__(self, adapter=None):
        self.adapter = adapter if adapter is not None else NetworkGraphAdapter()

    def draw_reaction_network(self, network, *, ax=None, positions=None, seed=42,
                              show_rates=True, show_deficiency=False, font_weight="bold"):
        """Draw directed reactions with separate curves for parallel/reverse edges."""
        graph = self.adapter.reaction_graph(network)
        return self._draw(network, graph, ax, positions, seed, show_rates, show_deficiency, font_weight)

    def draw_linkage_graph(self, network, *, ax=None, positions=None, seed=42,
                           show_rates=False, show_deficiency=False, font_weight="bold"):
        """Draw undirected complex connections colored by linkage class."""
        graph = self.adapter.linkage_graph(network)
        return self._draw(network, graph, ax, positions, seed, show_rates, show_deficiency, font_weight)

    def _draw(self, network, graph, ax, positions, seed, show_rates, show_deficiency, font_weight):
        nx = _networkx()
        try:
            from matplotlib.figure import Figure
            from matplotlib.lines import Line2D
            from matplotlib.patches import FancyArrowPatch
            from matplotlib.path import Path as DrawingPath
            from matplotlib import colormaps
        except ImportError as error:
            raise ImportError('Install visualization support: pip install "crntanalysis[visualization]"') from error

        if ax is None:
            ax = Figure(figsize=(10, 7), layout="constrained").subplots()
        components = sorted(nx.connected_components(graph.to_undirected()), key=min)
        if positions is None:
            # Lay out components independently so disconnected pairs do not collapse.
            from math import ceil, sqrt
            columns = max(1, ceil(sqrt(len(components))))
            positions = {}
            for i, nodes in enumerate(components):
                local = nx.spring_layout(graph.subgraph(sorted(nodes)), seed=seed, weight=None)
                for node, (x, y) in local.items():
                    positions[node] = (x + 3.5 * (i % columns), y - 3.5 * (i // columns))
        if any(node not in positions for node in graph):
            raise ValueError("Positions must include every complex index")
        colors = {node: colormaps["tab20"](i % 20) for i, nodes in enumerate(components) for node in nodes}
        nx.draw_networkx_nodes(graph, positions, node_color=[colors[n] for n in graph],
                               node_size=1800, ax=ax)
        nx.draw_networkx_labels(graph, positions,
                                labels={n: f"C{n}: {data['label']}" for n, data in graph.nodes(data=True)},
                                font_size=9, font_weight=font_weight, ax=ax)
        groups = {}
        for source, target, data in graph.edges(data=True):
            groups.setdefault(tuple(sorted((source, target))), []).append((source, target, data))
        for pair, edges in groups.items():
            for i, (source, target, data) in enumerate(edges):
                x1, y1 = positions[source]
                x2, y2 = positions[target]
                if source == target:
                    radius = 0.28 + i * 0.17
                    vertices = [(x1 - .06, y1 + .03), (x1 - radius, y1 + radius * 2),
                                (x1 + radius, y1 + radius * 2), (x1 + .06, y1 + .03)]
                    path = DrawingPath(vertices, [DrawingPath.MOVETO] + [DrawingPath.CURVE4] * 3)
                    label_position = (x1, y1 + radius * 1.5)
                else:
                    offset = (i - (len(edges) - 1) / 2) * .32
                    if source != pair[0]:
                        offset = -offset
                    midpoint = ((x1 + x2) / 2, (y1 + y2) / 2)
                    control = (midpoint[0] - offset * (y2 - y1), midpoint[1] + offset * (x2 - x1))
                    path = DrawingPath([(x1, y1), control, (x2, y2)],
                                       [DrawingPath.MOVETO, DrawingPath.CURVE3, DrawingPath.CURVE3])
                    label_position = ((midpoint[0] + control[0]) / 2, (midpoint[1] + control[1]) / 2)
                geometry = dict(path=path)
                if source != target:
                    geometry = dict(posA=(x1, y1), posB=(x2, y2),
                                    connectionstyle=f"arc3,rad={-offset}",
                                    shrinkA=22, shrinkB=22)
                patch = FancyArrowPatch(**geometry, arrowstyle="-|>" if graph.is_directed() else "-",
                                        mutation_scale=16, color="0.35", linewidth=1.4, zorder=1)
                ax.add_patch(patch)
                if show_rates:
                    reactions = [data["reaction"]] if graph.is_directed() else data["reactions"]
                    label = ", ".join(f"r{r.index}: {r.weight}" for r in reactions)
                    ax.text(*label_position, label, fontsize=8, fontweight=font_weight, ha="center", va="center",
                            bbox=dict(facecolor="white", edgecolor="none", alpha=.85))
        results = calculate_deficiency(network).linkage_classes if show_deficiency else None
        handles = []
        for i, nodes in enumerate(components):
            label = f"L{i}"
            if results is not None:
                label += f": δ={results[i].deficiency}"
            handles.append(Line2D([], [], marker="o", linestyle="", color=colors[min(nodes)], label=label))
        if handles:
            legend = ax.legend(handles=handles, title="Linkage classes", loc="best",
                               prop={"weight": font_weight})
            legend.get_title().set_fontweight(font_weight)
        ax.set_title("Reaction network" if graph.is_directed() else "Linkage graph",
                     fontweight=font_weight)
        ax.margins(.25)
        ax.set_axis_off()
        return ax.figure, ax

    @staticmethod
    def save(figure, path, *, dpi=150):
        """Save PNG, SVG, or PDF and return its Path; create parent folders."""
        path = Path(path)
        if path.suffix.lower() not in {".png", ".svg", ".pdf"}:
            raise ValueError("Use a .png, .svg, or .pdf output path")
        path.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(path, dpi=dpi, bbox_inches="tight")
        return path
