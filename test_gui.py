"""Integration checks for the Designer-backed desktop analysis workflow."""
import importlib.util
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
HAS_QT = importlib.util.find_spec('PySide6') is not None
if HAS_QT:
    from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QUrl
    from PySide6.QtGui import QDragEnterEvent, QDropEvent
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from GUI import mainwindow as gui
    from crntanalysis.orchestrator import CRNAnalysisService

ROOT = Path(__file__).resolve().parent


@unittest.skipUnless(HAS_QT, 'Install requirements.txt to test the desktop interface')
class DesktopAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = gui.MainWindow()
        self.window.ui.inputTabs.setCurrentIndex(0)

    def wait_for_analysis(self):
        deadline = time.monotonic() + 15
        while self.window.worker is not None and time.monotonic() < deadline:
            QTest.qWait(20)
        self.assertIsNone(self.window.worker, 'Background analysis did not finish')

    def tearDown(self):
        self.wait_for_analysis()
        self.window.close()
        self.app.processEvents()

    def test_text_analysis_and_input_invalidation(self):
        ui = self.window.ui
        self.assertFalse(ui.analyzeButton.isEnabled())
        ui.exampleButton.click()
        self.assertTrue(ui.analyzeButton.isEnabled())
        ui.analyzeButton.click()
        self.assertFalse(ui.analyzeButton.isEnabled())
        self.assertFalse(ui.inputTabs.isEnabled())
        self.wait_for_analysis()
        result = self.window.outcome.deficiency
        self.assertEqual((result.number_of_complexes, result.stoichiometric_rank,
                          result.number_of_linkage_classes, result.deficiency), (2, 1, 1, 0))
        self.assertIn('Linkage classes', ui.resultReport.toPlainText())
        self.assertIn('Network deficiency: 0', ui.resultsEmptyTitle.text())
        self.assertTrue(ui.inputTabs.isEnabled())
        ui.clearButton.click()
        self.assertIsNone(self.window.outcome)
        self.assertEqual(ui.resultReport.toPlainText(), '')
        self.assertFalse(ui.analyzeButton.isEnabled())

    def test_browsed_reaction_file_uses_backend(self):
        path = ROOT / 'Example_Data/crn1.react'
        with patch.object(gui.QFileDialog, 'getOpenFileName', return_value=(str(path), '')):
            self.window.ui.browseButton.click()
        self.window.ui.analyzeButton.click()
        self.wait_for_analysis()
        expected = CRNAnalysisService().analyze_file(path)
        self.assertEqual(self.window.outcome.to_dict(), expected.to_dict())
        self.assertEqual(self.window.outcome.deficiency.deficiency, 2)

    def test_dropped_ode_file_uses_backend(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'model.ode'
            path.write_text('ODE Model:\ndx/dt = -k1 * X\ndy/dt = k1 * X\n\nCoefficients:\nk1 = 0.5\n')
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(str(path))])
            frame = self.window.ui.dropZone
            enter = QDragEnterEvent(QPoint(5, 5), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
            QApplication.sendEvent(frame, enter)
            self.assertTrue(enter.isAccepted())
            drop = QDropEvent(QPointF(5, 5), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
            QApplication.sendEvent(frame, drop)
            self.assertTrue(drop.isAccepted())
            self.assertEqual(self.window.ui.formatCombo.currentIndex(), 1)
            self.window.ui.analyzeButton.click()
            self.wait_for_analysis()
            self.assertEqual(self.window.outcome.to_dict(), CRNAnalysisService().analyze_file(path).to_dict())

    def test_raw_ode_and_text_file_explicit_format(self):
        self.window.ui.formatCombo.setCurrentIndex(1)
        self.window.ui.exampleButton.click()
        text = self.window.ui.modelEditor.toPlainText()
        self.window.ui.analyzeButton.click()
        self.wait_for_analysis()
        self.assertEqual(self.window.outcome.to_dict(),
                         CRNAnalysisService().analyze_text(text, input_format='ode').to_dict())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'model.txt'
            path.write_text(text)
            self.window.select_file(path)
            self.window.ui.analyzeButton.click()
            self.wait_for_analysis()
            self.assertEqual(self.window.outcome.input_format, 'ode')
            self.assertEqual(self.window.outcome.deficiency.deficiency, 0)

    def test_invalid_input_error_then_recovery(self):
        self.window.ui.modelEditor.setPlainText('not a valid model')
        self.window.ui.analyzeButton.click()
        self.wait_for_analysis()
        self.assertIsNone(self.window.outcome)
        self.assertTrue(self.window.error_message)
        self.assertTrue(self.window.ui.resultReport.toPlainText())
        self.assertTrue(self.window.ui.analyzeButton.isEnabled())
        self.window.ui.clearButton.click()
        self.window.ui.exampleButton.click()
        self.window.ui.analyzeButton.click()
        self.wait_for_analysis()
        self.assertIsNotNone(self.window.outcome)
        self.assertIsNone(self.window.error_message)

    def test_removed_file_fails_without_crashing(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'missing.react'
            path.write_text('Reactions:\nA k1-> B')
            self.window.select_file(path)
            path.unlink()
            self.window.ui.analyzeButton.click()
            self.wait_for_analysis()
            self.assertIn('FileNotFoundError', self.window.error_message)
            self.assertTrue(self.window.ui.inputTabs.isEnabled())

    def test_designer_edit_is_loaded_on_next_launch(self):
        original = (ROOT / 'GUI/form.ui').read_text()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            (path / 'form.ui').write_text(original.replace('Your model, ready to explore.', 'Designer edit'))
            with patch.object(gui, '__file__', str(path / 'mainwindow.py')):
                other = gui.MainWindow()
                self.assertEqual(other.ui.titleLabel.text(), 'Designer edit')
                self.assertTrue((path / 'ui_form.py').exists())
                other.close()


if __name__ == '__main__':
    unittest.main()
