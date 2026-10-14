# Standalone desktop builds

This workflow keeps the Python package, CLI, GUI launcher, and development
Designer regeneration unchanged. It copies application sources into a temporary
directory, generates the UI there, and builds a standalone one-folder bundle.
The bundled GUI imports that generated UI without invoking Python subprocesses.
Only the three allowlisted public examples and project license are included;
research inputs and analysis outputs are not copied.

## Build

Use a dedicated environment on the operating system and architecture you want
to distribute for. Collaborators do not need Python, but the build machine does.

```bash
python3 -m venv .venv-build
```

Activate with `source .venv-build/bin/activate` on macOS/Linux, or
`.venv-build\Scripts\activate` in Windows Command Prompt. Then, from the root:

```bash
python -m pip install --upgrade pip
python -m pip install -r packaging/requirements-build.txt
python packaging/build_standalone.py
```

Outputs are under `dist/standalone/`:

- macOS: share `CRNTAnalysis.app` (compress it using Finder). Build separately
  for Apple Silicon and Intel unless using a verified universal environment.
- Windows: zip and share the entire `CRNTAnalysis` folder. Run its
  `CRNTAnalysis.exe`; do not send only the executable.
- Linux: share the entire `CRNTAnalysis` folder and run `CRNTAnalysis/CRNTAnalysis`.
  Verify compatibility with the target distribution and system libraries.

For another build, use a fresh destination, for example:

```bash
python packaging/build_standalone.py --output dist/standalone-next
```

The script refuses to overwrite an existing bundle. No installer is created.
This is a standalone application folder/bundle, not a single-file executable.
Public resources are inside the bundle's `resources` directory (under `_internal`
on Windows/Linux, and usually `Contents/Frameworks` on macOS).

## Verify before sharing

Test on a clean machine without Python or this repository installed:

1. Open the app and verify the version label.
2. Analyze a reaction file and each supplied ODE example with its stated options.
3. Inspect both graphs and auxiliary ODEs in the report.
4. Save text and structured reports to a user-selected directory and reopen them.
5. Check the bundle contains no research files or generated research reports.

Unsigned applications may trigger operating-system warnings. Signing and macOS
notarization are separate release steps. Include project and dependency license
notices as required before distribution; freezing does not remove those obligations.
