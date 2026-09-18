"""Designer supplies the layout; this module supplies application behavior."""
import runpy
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow, QMessageBox


def load_ui_class():
    """Regenerate the Designer form using the active Python environment's uic."""
    directory = Path(__file__).resolve().parent
    form_path = directory / 'form.ui'
    generated_path = directory / 'ui_form.py'
    try:
        result = subprocess.run(
            [sys.executable, '-c',
             'from PySide6.scripts.pyside_tool import uic; uic()', str(form_path)],
            capture_output=True, text=True, encoding='utf-8', timeout=30,
        )
        if result.returncode:
            raise RuntimeError(f'Could not compile {form_path}:\n{result.stderr.strip()}')
        # Compile before writing so a failed generation cannot replace the last file.
        compile(result.stdout, str(generated_path), 'exec')
        if not generated_path.exists() or generated_path.read_text(encoding='utf-8') != result.stdout:
            generated_path.write_text(result.stdout, encoding='utf-8')
        # Read the source afresh, avoiding cached imports when the form changes.
        return runpy.run_path(str(generated_path))['Ui_MainWindow']
    except (OSError, subprocess.TimeoutExpired, SyntaxError, KeyError) as error:
        raise RuntimeError(f'Could not load the Designer interface: {error}') from error


class FileDropHandler(QObject):
    """Attach drag-and-drop behavior to the existing Designer frame."""
    file_dropped = Signal(str)

    def __init__(self, frame):
        super().__init__(frame)
        self.frame = frame
        frame.setAcceptDrops(True)
        frame.installEventFilter(self)

    @staticmethod
    def local_file(event):
        urls = event.mimeData().urls()
        return len(urls) == 1 and urls[0].isLocalFile()

    def highlight(self, active):
        self.frame.setProperty('active', active)
        self.frame.style().unpolish(self.frame)
        self.frame.style().polish(self.frame)
        self.frame.update()

    def eventFilter(self, watched, event):
        kind = event.type()
        if kind in (QEvent.DragEnter, QEvent.DragMove):
            if self.local_file(event):
                event.acceptProposedAction()
                self.highlight(True)
            else:
                event.ignore()
                self.highlight(False)
            return True
        if kind == QEvent.DragLeave:
            self.highlight(False)
            event.accept()
            return True
        if kind == QEvent.Drop:
            self.highlight(False)
            if self.local_file(event):
                self.file_dropped.emit(event.mimeData().urls()[0].toLocalFile())
                event.acceptProposedAction()
            else:
                event.ignore()
            return True
        return super().eventFilter(watched, event)


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = load_ui_class()()
        self.ui.setupUi(self)
        self.selected_file = None
        self.reaction_placeholder = self.ui.modelEditor.placeholderText()
        self.ui.fileLabel.setTextFormat(Qt.PlainText)
        self.ui.formatCombo.currentIndexChanged.connect(self.update_placeholder)
        self.ui.modelEditor.textChanged.connect(self.update_state)
        self.ui.inputTabs.currentChanged.connect(self.update_state)
        self.ui.exampleButton.clicked.connect(self.load_example)
        self.ui.browseButton.clicked.connect(self.browse_file)
        self.ui.removeButton.clicked.connect(self.remove_file)
        # Clear is already connected to modelEditor.clear() in form.ui.
        self.drop_handler = FileDropHandler(self.ui.dropZone)
        self.drop_handler.file_dropped.connect(self.select_file)
        self.update_state()

    def update_placeholder(self):
        self.ui.modelEditor.setPlaceholderText(
            self.example_text() if self.ui.formatCombo.currentIndex() == 1
            else self.reaction_placeholder
        )

    def example_text(self):
        if self.ui.formatCombo.currentIndex() == 1:
            return 'ODE Model:\ndx/dt = -k1 * X\ndy/dt = k1 * X\n\nCoefficients:\nk1 = 0.5\n'
        return 'Reactions:\nX k1-> Y\nY k2-> X\n\nRate Constants:\nk1 = 0.5\nk2 = 0.2\n\nInitial Conditions:\nX = 1.0\nY = 0.0\n'

    def load_example(self):
        if self.ui.modelEditor.toPlainText().strip():
            answer = QMessageBox.question(self, 'Replace model text?', 'Loading an example will replace the text in the editor.', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:
                return
        self.ui.modelEditor.setPlainText(self.example_text())

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
        self.ui.fileLabel.setText(f'{path.name} · {size / 1024:.1f} KB')
        self.ui.fileLabel.setToolTip(str(path))
        self.ui.removeButton.setEnabled(True)
        if path.suffix.lower() in {'.react', '.ode'}:
            self.ui.formatCombo.setCurrentIndex(1 if path.suffix.lower() == '.ode' else 0)
        self.ui.inputTabs.setCurrentIndex(1)
        self.update_state()

    def remove_file(self):
        self.selected_file = None
        self.ui.fileLabel.setText('No file selected')
        self.ui.fileLabel.setToolTip('')
        self.ui.removeButton.setEnabled(False)
        self.update_state()

    def update_state(self):
        text = self.ui.modelEditor.toPlainText()
        self.ui.characterCount.setText(f'{len(text.splitlines()) if text else 0} lines · {len(text):,} characters')
        ready = bool(text.strip()) if self.ui.inputTabs.currentIndex() == 0 else self.selected_file is not None
        self.ui.statusLabel.setText('Input ready • Analysis is not connected in this design preview.' if ready else 'Ready • Paste text or select a model file.')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName('CRNTAnalysis')
    try:
        window = MainWindow()
    except RuntimeError as error:
        QMessageBox.critical(None, 'Unable to start CRNTAnalysis', str(error))
        sys.exit(1)
    window.show()
    sys.exit(app.exec())
