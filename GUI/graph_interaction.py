"""Animated Qt overlays and complex details for embedded Matplotlib graphs."""
import math
import time
from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QRadialGradient
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QLabel, QVBoxLayout, QWidget


class NodeGlow(QWidget):
    def __init__(self, canvas, interaction):
        super().__init__(canvas)
        self.interaction = interaction
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setStyleSheet('background: transparent;')

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        for index, color in [(self.interaction.selected, '#f5aa37'),
                             (self.interaction.hovered, '#409cff')]:
            if index is None:
                continue
            center = self.interaction.node_point(index)
            pulse = (math.sin(time.monotonic() * 4) + 1) / 2
            radius = self.interaction.node_radius(index) + 12 + 5 * pulse
            gradient = QRadialGradient(center, radius)
            shade = QColor(color)
            shade.setAlpha(0)
            gradient.setColorAt(0, shade)
            shade.setAlpha(25)
            gradient.setColorAt(.55, shade)
            shade.setAlpha(110 + int(35 * pulse))
            gradient.setColorAt(.76, shade)
            shade.setAlpha(0)
            gradient.setColorAt(1, shade)
            painter.setBrush(gradient)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(center, radius, radius)
        painter.end()


class GraphInteraction(QObject):
    def __init__(self, canvas, toolbar, axes, outcome):
        super().__init__(canvas)
        self.canvas, self.toolbar, self.axes, self.outcome = canvas, toolbar, axes, outcome
        self.nodes = list(outcome.network.complexes)
        self.artist = axes.collections[0] if axes.collections else None
        self.hovered = self.selected = None
        self.overlay = NodeGlow(canvas, self)
        self.overlay.setGeometry(canvas.rect())
        self.overlay.show()
        self.panel = QFrame(canvas)
        self.panel.setObjectName('complexDetails')
        self.panel.setStyleSheet('QFrame#complexDetails { background: white; border: 1px solid #a9c9f3; border-radius: 10px; } QLabel { background: transparent; color: #22334a; font-size: 12px; }')
        effect = QGraphicsDropShadowEffect(self.panel)
        effect.setBlurRadius(22)
        effect.setOffset(0, 4)
        effect.setColor(QColor(25, 64, 120, 65))
        self.panel.setGraphicsEffect(effect)
        self.panel.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout = QVBoxLayout(self.panel)
        layout.setContentsMargins(14, 12, 14, 12)
        self.details = QLabel()
        self.details.setTextFormat(Qt.PlainText)
        self.details.setWordWrap(True)
        self.details.setFixedWidth(280)
        layout.addWidget(self.details)
        self.panel.hide()
        self.timer = QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self.overlay.update)
        canvas.setMouseTracking(True)
        canvas.setFocusPolicy(Qt.StrongFocus)
        canvas.installEventFilter(self)
        self.connections = [canvas.mpl_connect(name, callback) for name, callback in [
            ('motion_notify_event', self.on_motion), ('button_press_event', self.on_click),
            ('figure_leave_event', self.on_leave), ('draw_event', self.on_draw),
        ]]

    def node_point(self, index):
        x, y = self.axes.transData.transform(self.artist.get_offsets()[index])
        ratio = self.canvas.devicePixelRatioF()
        return QPointF(x / ratio, self.canvas.height() - y / ratio)

    def node_radius(self, index):
        sizes = self.artist.get_sizes()
        size = sizes[index] if len(sizes) > 1 else sizes[0]
        return math.sqrt(size) / 2 * self.canvas.figure.dpi / 72 / self.canvas.devicePixelRatioF()

    def hit(self, event):
        if self.artist is None or event.inaxes != self.axes or self.toolbar.mode:
            return None
        contains, info = self.artist.contains(event)
        if not contains:
            return None
        return min(info['ind'], key=lambda index: sum((a - b) ** 2 for a, b in
                   zip(self.axes.transData.transform(self.artist.get_offsets()[index]), (event.x, event.y))))

    def on_motion(self, event):
        hovered = self.hit(event)
        if hovered != self.hovered:
            self.hovered = hovered
            self.refresh()

    def on_click(self, event):
        if event.button != 1 or self.toolbar.mode:
            return
        hit = self.hit(event)
        self.selected = None if hit == self.selected else hit
        self.hovered = hit
        self.canvas.setFocus()
        self.refresh()

    def on_leave(self, event=None):
        self.hovered = None
        self.refresh()

    def on_draw(self, event):
        self.overlay.setGeometry(self.canvas.rect())
        self.refresh()

    def refresh(self):
        active = self.hovered if self.hovered is not None else self.selected
        if active is None or not self.canvas.isVisible():
            self.timer.stop()
            self.panel.hide()
        else:
            if not self.timer.isActive():
                self.timer.start()
            self.details.setText(self.detail_text(active))
            self.panel.adjustSize()
            point = self.node_point(active)
            x, y = int(point.x() + self.node_radius(active) + 16), int(point.y() - 35)
            if x + self.panel.width() > self.canvas.width() - 10:
                x = int(point.x() - self.node_radius(active) - self.panel.width() - 16)
            self.panel.move(QPoint(max(10, min(x, self.canvas.width() - self.panel.width() - 10)),
                                  max(10, min(y, self.canvas.height() - self.panel.height() - 10))))
            self.panel.show()
            self.panel.raise_()
        self.overlay.update()

    def detail_text(self, index):
        complex_ = self.nodes[index]
        linkage = next(item for item in self.outcome.deficiency.linkage_classes if complex_.index in item.complex_indices)
        incoming = [r for r in self.outcome.network.reactions if r.target == complex_.index]
        outgoing = [r for r in self.outcome.network.reactions if r.source == complex_.index]
        incident = [r for r in self.outcome.network.reactions if r.source == complex_.index or r.target == complex_.index]
        labels = {item.index: item.label for item in self.nodes}
        lines = [f'C{complex_.index} · {complex_.label}', '',
                 'Composition: ' + (', '.join(f'{name}: {value}' for name, value in complex_.species.items()) or 'empty complex (0)'),
                 f'Linkage class L{linkage.index} · deficiency {linkage.deficiency}',
                 f'Incoming: {len(incoming)} · Outgoing: {len(outgoing)}', '', 'Connected reactions:']
        for reaction in incident[:6]:
            lines.append(f'r{reaction.index}: {labels[reaction.source]} → {labels[reaction.target]} (rate {reaction.weight})')
        if len(incident) > 6:
            lines.append(f'… and {len(incident) - 6} more')
        if not incident:
            lines.append('None (isolated complex)')
        lines.extend(['', 'Click a node to pin · Click empty space or Esc to clear'])
        return '\n'.join(lines)

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Hide, QEvent.Leave):
            self.on_leave()
            if event.type() == QEvent.Hide:
                self.timer.stop()
                self.panel.hide()
        elif event.type() == QEvent.Show:
            self.refresh()
        elif event.type() == QEvent.Resize:
            self.overlay.setGeometry(self.canvas.rect())
        elif event.type() == QEvent.KeyPress and event.key() == Qt.Key_Escape:
            self.hovered = self.selected = None
            self.refresh()
            return True
        return super().eventFilter(watched, event)

    def dispose(self):
        self.timer.stop()
        self.canvas.removeEventFilter(self)
        for connection in self.connections:
            self.canvas.mpl_disconnect(connection)
        self.panel.hide()
        self.overlay.hide()
        self.panel.deleteLater()
        self.overlay.deleteLater()
        self.deleteLater()
