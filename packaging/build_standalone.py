"""Build an isolated PyInstaller bundle without modifying project sources."""
import argparse
import importlib.util
import platform
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_EXAMPLES = (
    'rational_auxiliary_sectioned.ode',
    'rational_auxiliary_xpp.ode',
    'fractional_auxiliary.ode',
)


def prepare_sources(stage):
    """Copy only application packages and explicitly approved public resources."""
    for package in ('GUI', 'crntanalysis'):
        shutil.copytree(ROOT / package, stage / package,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo'))
    shutil.copy2(ROOT / 'packaging' / 'standalone_launcher.py', stage / 'launcher.py')
    resources = stage / 'resources'
    resources.mkdir()
    shutil.copy2(ROOT / 'LICENSE', resources / 'LICENSE')
    examples = resources / 'Example_Data'
    examples.mkdir()
    for filename in PUBLIC_EXAMPLES:
        shutil.copy2(ROOT / 'Example_Data' / filename, examples / filename)
    # Compile the copied Designer form, not GUI/ui_form.py in the worktree.
    subprocess.run(
        [sys.executable, '-c', 'from PySide6.scripts.pyside_tool import uic; uic()',
         str(stage / 'GUI' / 'form.ui'), '-o', str(stage / 'GUI' / 'ui_form.py')],
        check=True, cwd=stage,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist' / 'standalone',
                        help='Output directory (default: dist/standalone).')
    args = parser.parse_args(argv)
    required = ('PyInstaller', 'PySide6', 'sympy', 'networkx', 'matplotlib')
    missing = [name for name in required if importlib.util.find_spec(name) is None]
    if missing:
        parser.error('Missing build dependencies: ' + ', '.join(missing) +
                     '. Install packaging/requirements-build.txt in a separate virtual environment.')
    output = args.output.resolve()
    # Refuse overwrites: existing collaborator releases should not be lost.
    targets = [output / 'CRNTAnalysis', output / 'CRNTAnalysis.app']
    if any(path.exists() for path in targets):
        parser.error('A bundle already exists here. Choose a new --output directory.')
    with tempfile.TemporaryDirectory(prefix='crntanalysis-build-') as temporary:
        stage = Path(temporary) / 'source'
        stage.mkdir()
        prepare_sources(stage)
        command = [sys.executable, '-m', 'PyInstaller', '--noconfirm',
                   '--name', 'CRNTAnalysis', '--windowed', '--onedir',
                   '--paths', str(stage), '--distpath', str(output),
                   '--workpath', str(Path(temporary) / 'work'),
                   '--specpath', str(Path(temporary) / 'spec'),
                   '--add-data', str(stage / 'resources') + ':resources',
                   str(stage / 'launcher.py')]
        subprocess.run(command, check=True, cwd=stage)
    print(f'Built for {platform.system()} {platform.machine()}: {output}')
    print('Share the complete CRNTAnalysis folder, or CRNTAnalysis.app on macOS.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
