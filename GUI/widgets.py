"""Designer-compatible tabs with a soft text glow on hover."""
import math
from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QStyle, QStyleOptionTab, QTabBar, QTabWidget


class GlowTabBar(QTabBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.hovered = -1
        self.intensity = 0.0
        self.timer = QTimer(self)
        self.timer.setInterval(20)
        self.timer.timeout.connect(self.animate)

    def mouseMoveEvent(self, event):
        index = self.tabAt(event.position().toPoint())
        if index != self.hovered:
            self.hovered = index if index >= 0 and self.isTabEnabled(index) else -1
            self.intensity = 0.0
            self.timer.start()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.hovered = -1
        self.intensity = 0.0
        self.timer.stop()
        self.update()
        super().leaveEvent(event)

    def hideEvent(self, event):
        self.hovered = -1
        self.intensity = 0.0
        self.timer.stop()
        super().hideEvent(event)

    def animate(self):
        self.intensity = min(1.0, self.intensity + 0.12)
        self.update()
        if self.intensity == 1.0:
            self.timer.stop()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.hovered < 0:
            return
        option = QStyleOptionTab()
        self.initStyleOption(option, self.hovered)
        rect = self.style().subElementRect(QStyle.SE_TabBarTabText, option, self)
        painter = QPainter(self)
        font = self.font()
        font.setBold(self.hovered == self.currentIndex())
        painter.setFont(font)
        for radius, alpha in [(3, 14), (2, 22), (1, 30)]:
            painter.setPen(QColor(48, 141, 255, int(alpha * self.intensity)))
            for angle in range(0, 360, 45):
                offset = QPoint(round(radius * math.cos(math.radians(angle))),
                                round(radius * math.sin(math.radians(angle))))
                painter.drawText(rect.translated(offset), Qt.AlignCenter, option.text)
        painter.setPen(QColor('#176cd3'))
        painter.drawText(rect, Qt.AlignCenter, option.text)
        painter.end()


class GlowTabWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabBar(GlowTabBar(self))
