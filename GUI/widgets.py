"""Designer-compatible tabs with a crisp hover highlight.

Class names are retained for compatibility with the promoted Designer widgets.
Qt paints text normally; hover colors are defined in form.ui.
"""
from PySide6.QtWidgets import QTabBar, QTabWidget


class GlowTabBar(QTabBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)


class GlowTabWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabBar(GlowTabBar(self))
