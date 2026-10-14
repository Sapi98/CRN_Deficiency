"""Release workflow checks that do not require Qt or PyInstaller."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('standalone_build', ROOT / 'packaging' / 'build_standalone.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class StandaloneBuildTests(unittest.TestCase):
    def test_staging_preserves_development_ui_and_excludes_research(self):
        original = (ROOT / 'GUI' / 'ui_form.py').read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory)
            with patch.object(build.subprocess, 'run') as run:
                build.prepare_sources(stage)
            self.assertEqual((stage / 'GUI' / 'ui_form.py').read_bytes(), original)
            self.assertEqual(set(p.name for p in (stage / 'resources' / 'Example_Data').iterdir()),
                             set(build.PUBLIC_EXAMPLES))
            self.assertFalse((stage / 'Research_Models').exists())
            self.assertFalse((stage / 'Output').exists())
            command = run.call_args.args[0]
            self.assertEqual(command[-1], str(stage / 'GUI' / 'ui_form.py'))
        self.assertEqual((ROOT / 'GUI' / 'ui_form.py').read_bytes(), original)

    def test_missing_build_dependencies_have_actionable_message(self):
        with patch.object(build.importlib.util, 'find_spec', return_value=None):
            with self.assertRaises(SystemExit) as error:
                build.main([])
        self.assertEqual(error.exception.code, 2)

    def test_existing_release_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'CRNTAnalysis').mkdir()
            with patch.object(build.importlib.util, 'find_spec', return_value=True), \
                    patch.object(build.subprocess, 'run') as run:
                with self.assertRaises(SystemExit):
                    build.main(['--output', directory])
                run.assert_not_called()
