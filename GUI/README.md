# CRNTAnalysis desktop GUI

A PySide6 design preview with a text editor, reaction/ODE format selection,
examples, and file selection through drag and drop or a native file browser.
Selected files are displayed without reading or analyzing their contents.
The analysis button and results area are placeholders for future integration.

From the repository root:

```bash
python3 -m pip install -r GUI/requirements.txt
python3 GUI/mainwindow.py
```

## Editing the interface

`form.ui` is the single source for the layout, styling, labels, and widgets.
Edit it in Qt Creator / Qt Designer, save, then launch `mainwindow.py` again.
At startup, the app automatically regenerates `ui_form.py` using the active
Python environment's PySide6 compiler and calls `Ui_MainWindow.setupUi()`.
No manual generation command is required. Changes appear on the next launch;
an already open window does not reload automatically.

`ui_form.py` is generated code; do not edit it by hand. `mainwindow.py` contains
only startup and behavior (examples, file browsing, drag and drop, and status).
Keep the existing interactive widgets' object names when editing the design:
`formatCombo`, `modelEditor`, `inputTabs`, `characterCount`, `exampleButton`,
`clearButton`, `browseButton`, `removeButton`, `fileLabel`, `dropZone`, and
`statusLabel`. Layout, text, size, color, and position changes need no Python edits.
New controls that need application behavior require signal connections in Python
or Designer. The Clear connection is already stored in `form.ui`.

Both `python GUI/mainwindow.py` from the repository root and
`python mainwindow.py` from inside `GUI` work. The GUI directory must be writable
so the generated file can be updated.
