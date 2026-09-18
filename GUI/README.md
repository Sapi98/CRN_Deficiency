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

The interface is built directly in Python; generating `ui_form.py` is not required.
`form.ui` provides the matching editable layout for Qt Designer, including both
input tabs, the upload area, guidance, and results placeholders. The running app
currently builds its interface in Python; file handling lives in `mainwindow.py`.
