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
    from crntanalysis.orchestrator import AnalysisReportWriter, CRNAnalysisService

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(HAS_QT, 'Install requirements.txt to test the desktop interface')
class DesktopAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.question_patcher = patch.object(
            gui.QMessageBox, 'question', return_value=gui.QMessageBox.No
        )
        self.question_patcher.start()
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
        self.question_patcher.stop()

    def test_text_analysis_and_input_invalidation(self):
        ui = self.window.ui
        self.assertEqual(ui.previewBadge.text(), 'Desktop App v1.1')
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

    def test_fractional_example_with_explicit_ode_options(self):
        path = ROOT / 'Example_Data/fractional_auxiliary.ode'
        self.window.select_file(path)
        self.window.ui.allowFractionalCheck.setChecked(True)
        self.window.ui.liftRationalCheck.setChecked(True)
        self.window.ui.analyzeButton.click()
        self.assertFalse(self.window.ui.liftRationalCheck.isEnabled())
        self.wait_for_analysis()
        self.assertIsNone(self.window.error_message)
        expected = CRNAnalysisService().analyze_file(
            path, allow_fractional=True, lift_rational=True
        )
        self.assertEqual(self.window.outcome.to_dict(), expected.to_dict())
        self.window.ui.liftRationalCheck.setChecked(False)
        self.assertIsNone(self.window.outcome)

    def test_reaction_format_disables_ode_options(self):
        self.window.ui.formatCombo.setCurrentIndex(1)
        self.window.ui.liftRationalCheck.setChecked(True)
        self.window.ui.allowFractionalCheck.setChecked(True)
        self.window.ui.formatCombo.setCurrentIndex(0)
        self.assertFalse(self.window.ui.liftRationalCheck.isEnabled())
        self.window.ui.exampleButton.click()
        self.window.ui.analyzeButton.click()
        self.wait_for_analysis()
        self.assertIsNone(self.window.error_message)

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

    def test_save_dialog_supports_default_name_and_plain_text(self):
        outcome = CRNAnalysisService().analyze_text(
            self.window.example_text(), input_format='react'
        )
        self.window.display_outcome(outcome)
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'summary'
            with patch.object(
                gui.QFileDialog,
                'getSaveFileName',
                return_value=(str(target), 'Plain-text summary (*.txt)'),
            ), patch.object(gui.QMessageBox, 'information'):
                self.window.save_result()
            saved = target.with_suffix('.txt')
            self.assertTrue(saved.exists())
            self.assertIn('deficiency = 0', saved.read_text())

    def test_open_structured_result_restores_report_and_graph_data(self):
        self.window.show()
        self.app.processEvents()
        self.assertTrue(self.window.ui.openResultButton.isVisible())
        self.assertTrue(self.window.ui.openResultButton.isEnabled())
        self.assertTrue(self.window.open_result_action.isEnabled())
        self.assertFalse(self.window.ui.analyzeButton.isEnabled())
        self.assertFalse(self.window.ui.analysisTabs.isVisible())
        self.assertEqual(self.window.ui.resultsLayout.itemAt(1).layout(),
                         self.window.ui.resultActionsLayout)
        outcome = CRNAnalysisService().analyze_text(
            self.window.example_text(), input_format='react'
        )
        with tempfile.TemporaryDirectory() as folder:
            path = AnalysisReportWriter().write(outcome, folder, extension='output')
            with patch.object(
                gui.QFileDialog, 'getOpenFileName', return_value=(str(path), '')
            ):
                self.window.open_result_action.trigger()
        self.assertEqual(self.window.outcome.to_dict(), outcome.to_dict())
        self.assertIn('deficiency = 0', self.window.ui.resultReport.toPlainText())
        self.assertIs(self.window.graph_views[1].outcome, self.window.outcome)
        self.assertTrue(self.window.ui.saveResultButton.isEnabled())

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

    def test_read_only_installation_loads_fresh_designer_form(self):
        original = (ROOT / 'GUI/form.ui').read_text()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            (path / 'form.ui').write_text(original.replace('Your model, ready to explore.', 'Read-only package'))
            with patch.object(gui, '__file__', str(path / 'mainwindow.py')):
                with patch.object(Path, 'write_text', side_effect=PermissionError('Read-only installation')):
                    other = gui.MainWindow()
            self.assertEqual(other.ui.titleLabel.text(), 'Read-only package')
            self.assertFalse((path / 'ui_form.py').exists())
            other.close()

    @unittest.skipUnless(importlib.util.find_spec('matplotlib') and importlib.util.find_spec('networkx'),
                         'Graph dependencies not installed')
    def test_embedded_graphs_show_complexes_reactions_and_linkages(self):
        self.window.ui.exampleButton.click()
        self.window.ui.analyzeButton.click()
        self.wait_for_analysis()
        self.assertEqual(self.window.ui.previewBadge.text(), 'Desktop App v1.0')
        self.window.ui.analysisTabs.setCurrentIndex(1)
        reaction = self.window.graph_views[1]
        self.assertTrue(reaction.rendered, reaction.hint.text())
        axes = reaction.canvas.figure.axes[0]
        labels = [text.get_text() for text in axes.texts]
        self.assertIn('C0: X', labels)
        self.assertIn('C1: Y', labels)
        self.assertTrue(any('r0: 0.5' in label for label in labels))
        self.assertEqual(len(axes.patches), 2)
        self.assertEqual(axes.get_legend().get_texts()[0].get_text(), 'L0: δ=0')
        self.window.ui.analysisTabs.setCurrentIndex(2)
        linkage = self.window.graph_views[2]
        self.assertTrue(linkage.rendered, linkage.hint.text())
        self.assertEqual(len(linkage.canvas.figure.axes[0].patches), 1)
        # The same plot widgets are reused, with old contents removed on input edits.
        canvas = reaction.canvas
        self.window.ui.clearButton.click()
        self.assertIsNone(reaction.outcome)
        self.assertFalse(reaction.rendered)
        self.assertEqual(reaction.canvas.figure.axes, [])
        self.window.ui.exampleButton.click()
        self.window.ui.analyzeButton.click()
        self.wait_for_analysis()
        self.window.ui.analysisTabs.setCurrentIndex(1)
        self.assertIs(reaction.canvas, canvas)
        self.assertTrue(reaction.rendered, reaction.hint.text())

    @unittest.skipUnless(importlib.util.find_spec('matplotlib') and importlib.util.find_spec('networkx'),
                         'Graph dependencies not installed')
    def test_graph_failure_preserves_analysis_report(self):
        self.window.ui.exampleButton.click()
        self.window.ui.analyzeButton.click()
        self.wait_for_analysis()
        report = self.window.ui.resultReport.toPlainText()
        with patch('GUI.graph_view.NetworkVisualizer.draw_reaction_network', side_effect=ValueError('Graph test failure')):
            self.window.ui.analysisTabs.setCurrentIndex(1)
        self.assertIsNotNone(self.window.outcome)
        self.assertEqual(self.window.ui.resultReport.toPlainText(), report)
        self.assertIn('Could not draw graph', self.window.ui.reactionGraphHint.text())

    @unittest.skipUnless(importlib.util.find_spec('matplotlib') and importlib.util.find_spec('networkx'),
                         'Graph dependencies not installed')
    def test_node_hover_selection_details_and_cleanup(self):
        from matplotlib.backend_bases import MouseEvent
        self.window.show()
        self.window.ui.exampleButton.click()
        self.window.ui.analyzeButton.click()
        self.wait_for_analysis()
        self.window.ui.analysisTabs.setCurrentIndex(1)
        QTest.qWait(50)
        view = self.window.graph_views[1]
        interaction = view.interaction
        x, y = interaction.axes.transData.transform(interaction.artist.get_offsets()[0])
        motion = MouseEvent('motion_notify_event', view.canvas, x, y)
        view.canvas.callbacks.process('motion_notify_event', motion)
        self.assertEqual(interaction.hovered, 0)
        self.assertTrue(interaction.timer.isActive())
        self.assertTrue(interaction.panel.isHidden())
        click = MouseEvent('button_press_event', view.canvas, x, y, button=1)
        view.canvas.callbacks.process('button_press_event', click)
        self.assertEqual(interaction.selected, 0)
        self.assertFalse(interaction.panel.isHidden())
        self.assertIn('C0 · X', interaction.details.text())
        self.assertIn('Incoming: 1 · Outgoing: 1', interaction.details.text())
        self.assertIn('rate 0.5', interaction.details.text())
        other_x, other_y = interaction.axes.transData.transform(interaction.artist.get_offsets()[1])
        interaction.on_motion(MouseEvent('motion_notify_event', view.canvas, other_x, other_y))
        self.assertEqual(interaction.hovered, 1)
        self.assertIn('C0 · X', interaction.details.text())
        interaction.on_leave()
        self.assertIsNone(interaction.hovered)
        self.assertEqual(interaction.selected, 0)
        self.assertFalse(interaction.panel.isHidden())
        QTest.keyClick(view.canvas, Qt.Key_Escape)
        self.assertIsNone(interaction.selected)
        self.assertTrue(interaction.panel.isHidden())
        self.assertFalse(interaction.timer.isActive())
        # Pan/zoom must keep owning mouse gestures instead of selecting nodes.
        view.toolbar.pan()
        interaction.on_click(click)
        self.assertIsNone(interaction.selected)
        view.toolbar.pan()
        interaction.on_motion(motion)
        self.window.ui.analysisTabs.setCurrentIndex(0)
        self.app.processEvents()
        self.assertFalse(interaction.timer.isActive())
        self.window.ui.clearButton.click()
        self.assertIsNone(view.interaction)



if __name__ == '__main__':
    unittest.main()
