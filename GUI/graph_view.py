"""Embed the backend's complex graphs in Designer-provided graph containers."""

from crntanalysis.visualization import NetworkVisualizer
from GUI.graph_interaction import GraphInteraction


class GraphView:
    def __init__(self, layout, hint, kind):
        self.layout = layout
        self.hint = hint
        self.kind = kind
        self.description = hint.text()
        self.canvas = None
        self.toolbar = None
        self.outcome = None
        self.rendered = False
        self.interaction = None

    def clear(self):
        if self.interaction is not None:
            self.interaction.dispose()
            self.interaction = None
        self.outcome = None
        self.rendered = False
        if self.canvas is not None:
            self.canvas.figure.clear()
            self.toolbar.update()
            self.canvas.hide()
            self.toolbar.hide()
        self.hint.setText(self.description)

    def set_outcome(self, outcome):
        self.clear()
        self.outcome = outcome
        self.hint.setText('Select this tab to draw the graph.')

    def render(self):
        if self.outcome is None or self.rendered:
            return
        try:
            # Import only when a graph is requested, so analysis remains usable
            # if an existing environment has not installed the graph dependencies.
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
            from matplotlib.figure import Figure
            if self.canvas is None:
                self.canvas = FigureCanvasQTAgg(Figure(figsize=(10, 6), layout='constrained'))
                self.canvas.setMinimumHeight(420)
                self.toolbar = NavigationToolbar2QT(self.canvas, self.canvas.parent())
                self.layout.addWidget(self.toolbar)
                self.layout.addWidget(self.canvas)
            self.canvas.figure.clear()
            axes = self.canvas.figure.subplots()
            visualizer = NetworkVisualizer()
            draw = (visualizer.draw_reaction_network if self.kind == 'reaction'
                    else visualizer.draw_linkage_graph)
            draw(self.outcome.network, ax=axes, show_deficiency=True,
                 font_weight='bold' if self.layout.parentWidget().font().bold() else 'normal')
            self.toolbar.update()
            self.canvas.show()
            self.toolbar.show()
            self.canvas.draw()
            self.interaction = GraphInteraction(self.canvas, self.toolbar, axes, self.outcome)
            self.rendered = True
            self.hint.setText(self.description)
        except Exception as error:
            if self.canvas is not None:
                self.canvas.hide()
                self.toolbar.hide()
            self.hint.setText(f'Could not draw graph: {error}. Install or update the project dependencies and try again.')
