# Interactive web application

## Contents

- [Run locally](#run-locally)
- [Use the workspace](#use-the-workspace)
- [Deployment](#deployment)
- [Architecture and safeguards](#architecture-and-safeguards)
- [Tests](#tests)
- [Developer API](#developer-api)

## Run locally

The optional Dash/Cytoscape interface shares the existing scientific service.
Desktop, CLI, and standalone-build workflows are unchanged. From the root:

```bash
python3 -m venv .venv-web
source .venv-web/bin/activate
python -m pip install -r requirements-web.txt
python -m web.app
```

Open **http://127.0.0.1:8050**. Use `--port 8051` for another port. On Windows,
use `python` if `python3` is unavailable; activate with
`.venv-web\Scripts\activate.bat` (Command Prompt) or
`.venv-web\Scripts\Activate.ps1` (PowerShell).

The top-level `web/` directory is a repository application, not part of the
installable `crntanalysis` module. Pip installs include no web app, web entry
point, or web dependency extra. Launch it from a repository checkout using
`python -m web.app`. The separate web requirements do not install Qt or
Matplotlib. Do not expose the development server publicly.

## Use the workspace

1. Choose a public example, paste a document, or upload a UTF-8 `.react`, `.ode`,
   or `.txt` file. Uploads replace the editor content.
2. Select format, unresolved-parameter policy, and applicable ODE options.
   Examples select their options automatically; uploads do not silently opt in.
3. Click **Analyze network**. Editing input invalidates earlier results.
4. Drag nodes, pan/zoom, switch reaction/linkage views, select a layout, filter
   linkage classes, or highlight complexes using the search field.
5. Click nodes or edges for composition or reaction details. Parallel channels
   retain distinct IDs; linkage edges aggregate channel labels.
6. Download the current graph as PNG or the full report as `.txt` / `.analysis`.
   Structured downloads can be opened in the desktop application.

Graph labels round rates; scientific data retains precision. Reports include
indexed complexes, original/augmented ODEs, auxiliary definitions, and warnings.
Scientific limitations of selected or augmented realizations remain unchanged.

## Deployment

```bash
docker build -f Dockerfile.web -t crntanalysis-web .
docker run --rm --memory=2g --cpus=2 -p 127.0.0.1:8050:8050 crntanalysis-web
```

The image runs Gunicorn with two synchronous workers as an unprivileged user.
Explicit copies and `.dockerignore` exclude private research inputs, reports,
Git metadata, environments, and desktop files. Examples are generic strings
embedded in the web adapter, not research files loaded from disk.

For shared access, configure an HTTPS reverse proxy, authentication, request
rate limits, and container CPU/memory limits. Keep server/proxy timeouts longer
than the 20-second analysis budget. Do not log request bodies. No hosting
account is created or service published by this local implementation.

## Architecture and safeguards

Dash callbacks call `AnalysisRunner`, which starts a fresh spawned process
running `CRNAnalysisService`. `ConsoleReportFormatter` supplies the report;
`GraphPresenter` turns serialized outcomes into Cytoscape elements. No science
is reimplemented in JavaScript. Browser graph layouts do not change the CRN.

- No module-global user-result cache and no uploaded model files written to disk.
- Results use browser memory storage, not persistent local/session storage.
  Refresh clears results; tabs have independent stores.
- Models are processed on the server. Use localhost or an institution-controlled
  host for unpublished research. Hosting/proxy logs are outside app control.
- Limits: 32 KB model input, 20 seconds per analysis, 500 complexes, 1500
  reactions, and 1 MB serialized results. HTTP bodies are capped at 2.5 MB to
  accommodate bounded result state sent back to graph callbacks.
- Linux analysis children have a 1 GiB address-space ceiling. Other operating
  systems retain the timeout but need deployment-level memory controls.
- Child processes are terminated and reaped after completion, failure, or timeout.
  Synchronous Gunicorn workers bound concurrent requests per instance.
- These controls are not a full hostile-code sandbox or DDoS defense. Public
  deployment needs operational hardening, dependency auditing, and version pins.

This version does not include logins, saved-project accounts, collaborative
editing, or retained server-side reports. Large networks belong in the desktop
or Python workflow. Web build requirements use compatible ranges, not a lockfile.

## Tests

```bash
python -m unittest discover -s tests -p test_web.py
python -m unittest discover -s tests
```

Tests cover generic examples, upload validation, graph filtering, parallel
channels, process errors/timeouts, Dash routes/assets, and HTTP analysis callbacks.
Web HTTP tests skip without Dash; desktop/plotting tests may skip in a headless
environment. Browser interaction and Docker builds also require manual release
verification on the intended hosting platform.

## Developer API

`web.service` has no Dash dependency; `app` imports Dash only when
creating the interface. `wsgi` creates the production app/server on import.

### `decode_upload` — public

```python
def decode_upload(contents, filename)
```

#### Parameters

| Name | Type | Default | Purpose |
|---|---|---|---|
| `contents` | `str` | required | Base64 data URL supplied by the upload control. |
| `filename` | `str` | required | Uploaded name; used only for extension validation. |

#### Returns

- `text` (`str`): Validated UTF-8 model, without writing a file.

#### Raises

- `ValueError`: Invalid extension, encoding, data URL, or input size.

### `analyze_document` — public

```python
def analyze_document(text, input_format='auto', options=(), unresolved='symbolic')
```

#### Parameters

| Name | Type | Default | Purpose |
|---|---|---|---|
| `text` | `str` | required | Model document. |
| `input_format` | `str` | `'auto'` | `auto`, `react`, or `ode`. |
| `options` | `Sequence[str]` | `()` | `lift` and/or `fractional`. |
| `unresolved` | `str` | `'symbolic'` | Existing unresolved-value policy. |

#### Returns

- `payload` (`dict`): JSON-safe `outcome` and human-readable `report`.

#### Raises

- `ValueError`: Invalid/oversized model, parser or deficiency errors, or oversized result.

### `AnalysisRunner` — public

```python
def __init__(self, timeout=20)
def run(self, text, input_format, options, unresolved)
```

#### Parameters

| Name | Type | Default | Purpose |
|---|---|---|---|
| `timeout` | `float` | `20` | Child-process wall-clock budget in seconds. |
| `text` | `str` | required | Model input to `run`. |
| `input_format` | `str` | required | Format selector. |
| `options` | `Sequence[str]` | required | ODE options. |
| `unresolved` | `str` | required | Unresolved-value policy. |

#### Returns

- `payload` (`dict`): Successful analysis result from `run`.

#### Raises

- `ValueError`: Input rejection, analysis failure, worker exit, or timeout.

### `GraphPresenter.elements` — public

```python
def elements(self, payload, mode='reaction', linkage='all')
```

#### Parameters

| Name | Type | Default | Purpose |
|---|---|---|---|
| `payload` | `dict` or `None` | required | Serialized web result. |
| `mode` | `str` | `'reaction'` | Directed reactions or undirected linkage graph. |
| `linkage` | `str` | `'all'` | Linkage-class index or all classes. |

#### Returns

- `elements` (`list[dict]`): Cytoscape node and edge data, including details and colors.

### `format_rate` — public

```python
def format_rate(value)
```

#### Parameters

| Name | Type | Default | Purpose |
|---|---|---|---|
| `value` | `float`, `int`, or `str` | required | Rate to display. |

#### Returns

- `label` (`str`): Rounded display value or symbolic label; no scientific data is modified.

### `create_app` and `main` — public

```python
def create_app(runner=None)
def main()
```

#### Parameters

| Name | Type | Default | Purpose |
|---|---|---|---|
| `runner` | `AnalysisRunner` or compatible object | `None` | Injectable analysis executor for `create_app`. |

#### Returns

- `app` (`dash.Dash`): Independent application from `create_app`.

#### Raises

- `ImportError`: Optional web dependencies are missing.
- `SystemExit`: `main` command-line help or argument errors.

### Private implementation

`_analysis_worker(connection, arguments)` transports results/errors and applies
the Linux memory limit. The nested `app` callbacks manage loading, analysis,
metrics, graph rendering/layout/style, inspection, and downloads. They are not
a stable external API; HTTP callback tests cover their contracts. No application
state is stored in shared mutable module-level result objects.
