"""CRNTAnalysis desktop interface. Analysis integration is intentionally deferred."""
import sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea,
    QTabWidget, QVBoxLayout, QWidget,
)


STYLE = """
QWidget { font-family: 'Segoe UI', 'Helvetica Neue', sans-serif; font-size: 14px;
          color: #22334a; background: #f4f6fa; }
QFrame#header, QFrame#card { background: white; border: 1px solid #e0e6ef; border-radius: 12px; }
QFrame#header { border-radius: 0; border: none; border-bottom: 1px solid #e0e6ef; }
QWidget#inputPage { background: white; }
QLabel { background: transparent; }
QLabel#brand { font-size: 19px; font-weight: 700; }
QLabel#title { font-size: 29px; font-weight: 700; }
QLabel#subtitle, QLabel#muted { color: #69788d; }
QLabel#section { font-size: 17px; font-weight: 600; }
QLabel#badge { color: #397d74; background: #eaf5f1; border-radius: 10px; padding: 6px 12px; }
QLabel#symbol { color: #246dce; background: #edf4ff; border-radius: 12px; font-size: 25px; padding: 10px; }
QPushButton { background: white; border: 1px solid #d6deea; border-radius: 7px; padding: 9px 16px; font-weight: 600; }
QPushButton:hover { background: #edf4ff; border-color: #a6c4ef; }
QPushButton:pressed { background: #deebff; }
QPushButton#primary { background: #246dce; color: white; border: none; }
QPushButton#primary:disabled { background: #e9edf3; color: #8b97a7; }
QPushButton#primary:hover { background: #1b5ab0; }
QPushButton:disabled { background: #e9edf3; color: #8b97a7; border-color: #e1e6ee; }
QPushButton:focus, QComboBox:focus { border: 2px solid #246dce; }
QTabWidget::pane { background: white; border: none; }
QTabBar::tab { background: white; color: #718097; padding: 12px 20px; border-bottom: 2px solid #e5eaf1; }
QTabBar::tab:selected { color: #246dce; border-bottom: 2px solid #246dce; font-weight: 600; }
QPlainTextEdit { font-family: 'Menlo', 'Consolas', monospace; background: #fafbfd; border: 1px solid #dfe6f0; border-radius: 8px; padding: 12px; selection-background-color: #c6ddff; }
QPlainTextEdit:focus { border: 1px solid #246dce; }
QComboBox { background: white; border: 1px solid #d6deea; border-radius: 6px; padding: 7px 12px; min-width: 145px; }
QComboBox QAbstractItemView { background: white; selection-background-color: #deebff; }
QFrame#drop { background: #fafcff; border: 2px dashed #bccce2; border-radius: 12px; }
QFrame#drop[active="true"] { background: #edf4ff; border-color: #246dce; }
QScrollArea { border: none; }
"""


def label(text, name=None):
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(True)
    return widget


class DropZone(QFrame):
    file_dropped = Signal(str)
    browse_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName('drop')
        self.setAcceptDrops(True)
        self.setMinimumHeight(260)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 30, 28, 30)
        layout.addStretch()
        for text, name in [('↑', 'symbol'), ('Drop your model file here', 'section'),
                           ('or choose a file from your computer', 'muted')]:
            item = label(text, name)
            item.setAlignment(Qt.AlignCenter)
            layout.addWidget(item)
        button = QPushButton('Browse files…')
        button.clicked.connect(self.browse_requested.emit)
        layout.addWidget(button, alignment=Qt.AlignCenter)
        formats = label('Supported formats: .react, .ode, .txt', 'muted')
        formats.setAlignment(Qt.AlignCenter)
        layout.addWidget(formats)
        layout.addStretch()

    @staticmethod
    def local_file(event):
        urls = event.mimeData().urls()
        return len(urls) == 1 and urls[0].isLocalFile()

    def highlight(self, active):
        self.setProperty('active', active)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event):
        if self.local_file(event):
            event.acceptProposedAction()
            self.highlight(True)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.highlight(False)
        event.accept()

    def dropEvent(self, event):
        self.highlight(False)
        if self.local_file(event):
            self.file_dropped.emit(event.mimeData().urls()[0].toLocalFile())
            event.acceptProposedAction()
        else:
            event.ignore()


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_file = None
        self.setWindowTitle('CRNTAnalysis • Model workspace')
        self.resize(1120, 850)
        self.setMinimumSize(780, 640)
        self.setStyleSheet(STYLE)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = QFrame()
        header.setObjectName('header')
        header_row = QHBoxLayout(header)
        header_row.setContentsMargins(32, 18, 32, 18)
        header_row.addWidget(label('CRNTAnalysis', 'brand'))
        header_row.addWidget(label('Chemical Reaction Network Theory', 'muted'))
        header_row.addStretch()
        header_row.addWidget(label('Design preview', 'badge'))
        layout.addWidget(header)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        body = QWidget()
        scroll.setWidget(body)
        content = QVBoxLayout(body)
        content.setContentsMargins(32, 28, 32, 24)
        content.setSpacing(20)
        content.addWidget(label('Your model, ready to explore.', 'title'))
        content.addWidget(label('Paste a reaction network or upload a model file to get started.', 'subtitle'))
        columns = QHBoxLayout()
        columns.setSpacing(20)
        content.addLayout(columns)
        input_card = QFrame()
        input_card.setObjectName('card')
        input_layout = QVBoxLayout(input_card)
        input_layout.setContentsMargins(22, 22, 22, 22)
        input_layout.setSpacing(16)
        top = QHBoxLayout()
        top.addWidget(label('01  /  Model input', 'section'))
        top.addStretch()
        top.addWidget(label('Format', 'muted'))
        self.format = QComboBox()
        self.format.addItems(['Reaction network', 'ODE model'])
        self.format.setAccessibleName('Model input format')
        self.format.currentIndexChanged.connect(self.update_placeholder)
        top.addWidget(self.format)
        input_layout.addLayout(top)
        self.tabs = QTabWidget()
        input_layout.addWidget(self.tabs)
        text_page = QWidget()
        text_page.setObjectName('inputPage')
        text_layout = QVBoxLayout(text_page)
        text_layout.setContentsMargins(0, 16, 0, 0)
        text_layout.addWidget(label('Paste or write your model below.', 'muted'))
        self.editor = QPlainTextEdit()
        self.editor.setAccessibleName('Model text')
        self.editor.setMinimumHeight(255)
        self.editor.setFont(QFont('Menlo', 12))
        self.editor.textChanged.connect(self.update_state)
        text_layout.addWidget(self.editor)
        text_footer = QHBoxLayout()
        self.count = label('0 lines · 0 characters', 'muted')
        self.count.setWordWrap(False)
        text_footer.addWidget(self.count)
        text_footer.addStretch()
        example = QPushButton('Load example')
        example.clicked.connect(self.load_example)
        clear = QPushButton('Clear')
        clear.clicked.connect(self.editor.clear)
        text_footer.addWidget(example)
        text_footer.addWidget(clear)
        text_layout.addLayout(text_footer)
        self.tabs.addTab(text_page, 'Paste text')
        upload_page = QWidget()
        upload_page.setObjectName('inputPage')
        upload_layout = QVBoxLayout(upload_page)
        upload_layout.setContentsMargins(0, 16, 0, 0)
        self.drop_zone = DropZone()
        self.drop_zone.browse_requested.connect(self.browse_file)
        self.drop_zone.file_dropped.connect(self.select_file)
        upload_layout.addWidget(self.drop_zone)
        file_row = QHBoxLayout()
        self.file_label = label('No file selected', 'muted')
        self.file_label.setTextFormat(Qt.PlainText)
        file_row.addWidget(self.file_label, 1)
        self.remove = QPushButton('Remove')
        self.remove.clicked.connect(self.remove_file)
        self.remove.setEnabled(False)
        file_row.addWidget(self.remove)
        upload_layout.addLayout(file_row)
        self.tabs.addTab(upload_page, 'Upload file')
        self.tabs.currentChanged.connect(self.update_state)
        action_row = QHBoxLayout()
        action_row.addWidget(label('Analysis will be available in a future update.', 'muted'), 1)
        self.analyze = QPushButton('Analyze model  →')
        self.analyze.setObjectName('primary')
        self.analyze.setEnabled(False)
        self.analyze.setToolTip('Design preview: analysis is not connected yet.')
        action_row.addWidget(self.analyze)
        input_layout.addLayout(action_row)
        columns.addWidget(input_card, 3)
        guide = QFrame()
        guide.setObjectName('card')
        guide.setMaximumWidth(270)
        guide_layout = QVBoxLayout(guide)
        guide_layout.setContentsMargins(22, 22, 22, 22)
        guide_layout.setSpacing(16)
        guide_layout.addWidget(label('A little guidance', 'section'))
        guide_layout.addWidget(label('Reaction networks', 'section'))
        guide_layout.addWidget(label('Use a Reactions: section with one reaction per line. Add rate constants and initial conditions as needed.', 'muted'))
        guide_layout.addWidget(label('ODE models', 'section'))
        guide_layout.addWidget(label('Use an ODE Model: section with mass-action equations, followed by a Coefficients: section.', 'muted'))
        guide_layout.addWidget(label('File input', 'section'))
        guide_layout.addWidget(label('Select one .react, .ode, or .txt file. For .txt files, choose the matching format above.', 'muted'))
        guide_layout.addStretch()
        columns.addWidget(guide, 1)
        results = QFrame()
        results.setObjectName('card')
        results_layout = QVBoxLayout(results)
        results_layout.setContentsMargins(22, 20, 22, 20)
        results_layout.addWidget(label('02  /  Analysis overview', 'section'))
        for text, name in [
            ('Your network insights will appear here', 'section'),
            ('Complexes   ·   Linkage classes   ·   Stoichiometric rank   ·   Deficiency', 'muted'),
            ('Awaiting analysis integration', 'muted'),
        ]:
            item = label(text, name)
            item.setAlignment(Qt.AlignCenter)
            results_layout.addWidget(item)
        content.addWidget(results)
        self.status = label('Ready • Paste text or select a model file.', 'muted')
        content.addWidget(self.status)
        content.addStretch()
        self.update_placeholder()

    def update_placeholder(self):
        self.editor.setPlaceholderText(self.example_text())

    def example_text(self):
        if self.format.currentIndex() == 1:
            return 'ODE Model:\ndx/dt = -k1 * X\ndy/dt = k1 * X\n\nCoefficients:\nk1 = 0.5\n'
        return 'Reactions:\nX k1-> Y\nY k2-> X\n\nRate Constants:\nk1 = 0.5\nk2 = 0.2\n\nInitial Conditions:\nX = 1.0\nY = 0.0\n'

    def load_example(self):
        if self.editor.toPlainText().strip():
            answer = QMessageBox.question(self, 'Replace model text?', 'Loading an example will replace the text in the editor.', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:
                return
        self.editor.setPlainText(self.example_text())

    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Select a model file', '', 'Model files (*.react *.ode *.txt)')
        if path:
            self.select_file(path)

    def select_file(self, filename):
        path = Path(filename)
        if not path.is_file() or path.suffix.lower() not in {'.react', '.ode', '.txt'}:
            QMessageBox.warning(self, 'Unsupported file', 'Choose a single .react, .ode, or .txt file.')
            return
        try:
            size = path.stat().st_size
        except OSError as error:
            QMessageBox.warning(self, 'File unavailable', str(error))
            return
        self.selected_file = path
        self.file_label.setText(f'{path.name} · {size / 1024:.1f} KB')
        self.file_label.setToolTip(str(path))
        self.remove.setEnabled(True)
        if path.suffix.lower() in {'.react', '.ode'}:
            self.format.setCurrentIndex(1 if path.suffix.lower() == '.ode' else 0)
        self.tabs.setCurrentIndex(1)
        self.update_state()

    def remove_file(self):
        self.selected_file = None
        self.file_label.setText('No file selected')
        self.file_label.setToolTip('')
        self.remove.setEnabled(False)
        self.update_state()

    def update_state(self):
        text = self.editor.toPlainText()
        self.count.setText(f'{len(text.splitlines()) if text else 0} lines · {len(text):,} characters')
        ready = bool(text.strip()) if self.tabs.currentIndex() == 0 else self.selected_file is not None
        self.status.setText('Input ready • Analysis is not connected in this design preview.' if ready else 'Ready • Paste text or select a model file.')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName('CRNTAnalysis')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
