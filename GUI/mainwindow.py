"""Designer supplies the layout; this module supplies application behavior."""
import runpy
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QThread, Qt, Signal
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow, QMessageBox


# Support launching the script from either the repository root or GUI directory.
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crntanalysis.orchestrator import CRNAnalysisService, ConsoleReportFormatter
from GUI.graph_view import GraphView


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
            try:
                generated_path.write_text(result.stdout, encoding='utf-8')
            except PermissionError:
                # Installed package directories can be read-only. Use the fresh
                # generated interface in memory without changing the installation.
                namespace = {'__file__': str(generated_path), '__name__': 'ui_form'}
                exec(compile(result.stdout, str(generated_path), 'exec'), namespace)
                return namespace['Ui_MainWindow']
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


class AnalysisWorker(QThread):
    """Keep parsing and symbolic calculations off the interface thread."""
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, source, input_format, is_file, parent=None):
        super().__init__(parent)
        self.source = source
        self.input_format = input_format
        self.is_file = is_file

    def run(self):
        try:
            service = CRNAnalysisService()
            if self.is_file:
                outcome = service.analyze_file(self.source, input_format=self.input_format)
            else:
                outcome = service.analyze_text(self.source, input_format=self.input_format)
            self.succeeded.emit(outcome)
        except Exception as error:
            # Exceptions must cross the thread boundary as data, never escape run().
            self.failed.emit(f'{type(error).__name__}: {error}')


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = load_ui_class()()
        self.ui.setupUi(self)
        self.selected_file = None
        self.worker = None
        self.outcome = None
        self.error_message = None
        self.reaction_placeholder = self.ui.modelEditor.placeholderText()
        self.ui.fileLabel.setTextFormat(Qt.PlainText)
        self.ui.formatCombo.currentIndexChanged.connect(self.update_placeholder)
        self.ui.modelEditor.textChanged.connect(self.input_changed)
        self.ui.inputTabs.currentChanged.connect(self.input_changed)
        self.ui.formatCombo.currentIndexChanged.connect(self.input_changed)
        self.ui.analyzeButton.clicked.connect(self.analyze_model)
        self.ui.exampleButton.clicked.connect(self.load_example)
        self.ui.browseButton.clicked.connect(self.browse_file)
        self.ui.removeButton.clicked.connect(self.remove_file)
        # Clear is already connected to modelEditor.clear() in form.ui.
        self.drop_handler = FileDropHandler(self.ui.dropZone)
        self.drop_handler.file_dropped.connect(self.select_file)
        self.graph_views = {
            1: GraphView(self.ui.reactionGraphLayout, self.ui.reactionGraphHint, 'reaction'),
            2: GraphView(self.ui.linkageGraphLayout, self.ui.linkageGraphHint, 'linkage'),
        }
        self.ui.analysisTabs.currentChanged.connect(self.render_graph)
        self.ui.analysisTabs.hide()
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
        if self.worker is not None:
            return
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
        self.input_changed()

    def remove_file(self):
        self.selected_file = None
        self.ui.fileLabel.setText('No file selected')
        self.ui.fileLabel.setToolTip('')
        self.ui.removeButton.setEnabled(False)
        self.input_changed()

    def input_ready(self):
        return (bool(self.ui.modelEditor.toPlainText().strip())
                if self.ui.inputTabs.currentIndex() == 0 else self.selected_file is not None)

    def input_changed(self):
        self.outcome = None
        self.error_message = None
        self.ui.resultsEmptyTitle.setText('Your network insights will appear here')
        self.ui.resultsMetrics.setText('Complexes   ·   Linkage classes   ·   Stoichiometric rank   ·   Deficiency')
        self.ui.resultsHint.setText('Select an input and click Analyze model.')
        self.ui.resultReport.clear()
        self.ui.analysisTabs.hide()
        for view in self.graph_views.values():
            view.clear()
        self.update_state()

    def update_state(self):
        text = self.ui.modelEditor.toPlainText()
        self.ui.characterCount.setText(f'{len(text.splitlines()) if text else 0} lines · {len(text):,} characters')
        busy = self.worker is not None
        self.ui.analyzeButton.setEnabled(self.input_ready() and not busy)
        self.ui.analyzeButton.setText('Analyzing…' if busy else 'Analyze model  →')
        self.ui.inputTabs.setEnabled(not busy)
        self.ui.formatCombo.setEnabled(not busy)
        if busy:
            message = 'Analyzing your model…'
        elif self.error_message:
            message = 'Analysis failed • Correct your input and try again.'
        elif self.outcome is not None:
            message = 'Analysis complete.'
        elif self.input_ready():
            message = 'Input ready • Click Analyze model.'
        else:
            message = 'Ready • Paste text or select a model file.'
        self.ui.statusLabel.setText(message)

    def analyze_model(self):
        if self.worker is not None or not self.input_ready():
            return
        self.input_changed()
        is_file = self.ui.inputTabs.currentIndex() == 1
        source = self.selected_file if is_file else self.ui.modelEditor.toPlainText()
        input_format = 'ode' if self.ui.formatCombo.currentIndex() == 1 else 'react'
        self.worker = AnalysisWorker(source, input_format, is_file, self)
        self.worker.succeeded.connect(self.show_outcome)
        self.worker.failed.connect(self.show_error)
        self.worker.finished.connect(self.analysis_finished)
        self.update_state()
        self.worker.start()

    def show_outcome(self, outcome):
        self.outcome = outcome
        result = outcome.deficiency
        self.ui.resultsEmptyTitle.setText(f'Network deficiency: {result.deficiency}')
        self.ui.resultsMetrics.setText(
            f'Complexes: {result.number_of_complexes}   ·   '
            f'Linkage classes: {result.number_of_linkage_classes}   ·   '
            f'Stoichiometric rank: {result.stoichiometric_rank}'
        )
        self.ui.resultsHint.setText(
            f'{len(result.species)} species · {len(outcome.network.reactions)} reactions'
            + (' · Generic symbolic rank' if result.symbolic_rank else '')
            + (f' · {len(outcome.warnings)} warnings (see report)' if outcome.warnings else '')
        )
        self.ui.resultReport.setPlainText(ConsoleReportFormatter().format(outcome))
        for view in self.graph_views.values():
            view.set_outcome(outcome)
        self.ui.analysisTabs.setTabEnabled(1, True)
        self.ui.analysisTabs.setTabEnabled(2, True)
        self.ui.analysisTabs.show()
        self.render_graph(self.ui.analysisTabs.currentIndex())

    def render_graph(self, index):
        view = self.graph_views.get(index)
        if view is not None:
            view.render()

    def show_error(self, message):
        self.error_message = message
        self.ui.resultsEmptyTitle.setText('Unable to analyze this model')
        self.ui.resultsHint.setText('Check the model format and the error below, then try again.')
        self.ui.resultReport.setPlainText(message)
        self.ui.analysisTabs.setCurrentIndex(0)
        self.ui.analysisTabs.setTabEnabled(1, False)
        self.ui.analysisTabs.setTabEnabled(2, False)
        self.ui.analysisTabs.show()

    def analysis_finished(self):
        worker = self.worker
        self.worker = None
        worker.deleteLater()
        self.update_state()

    def closeEvent(self, event):
        if self.worker is not None:
            self.ui.statusLabel.setText('Please wait for the current analysis to finish before closing.')
            event.ignore()
        else:
            super().closeEvent(event)


def main():
    """Launch the desktop interface from a script or installed GUI command."""
    app = QApplication(sys.argv)
    app.setApplicationName('CRNTAnalysis')
    try:
        window = MainWindow()
    except RuntimeError as error:
        QMessageBox.critical(None, 'Unable to start CRNTAnalysis', str(error))
        return 1
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
