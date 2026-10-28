# Interactive web application

## Contents

- [Run locally](#run-locally)
- [Use the workspace](#use-the-workspace)
- [Deployment](#deployment)
  - [Managed Docker hosting](#managed-docker-hosting)
  - [University or private server](#university-or-private-server)
  - [Pre-launch verification and operations](#pre-launch-verification-and-operations)
- [Architecture and safeguards](#architecture-and-safeguards)
- [Tests](#tests)
- [Larger models and deployment settings](#larger-models-and-deployment-settings)
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
6. Large diagrams are paged (300 complexes / 1000 rendered edges by default).
   Choose a graph page or enter a complex index such as `C123` to inspect its
   one-hop neighborhood. Linkage filtering works with either view. The status
   line explicitly reports hidden cross-page or excess edges. The calculation
   and report downloads always retain the complete accepted network.
7. Download the current graph page as PNG or the full report as `.txt` / `.analysis`.
   Structured downloads can be opened in the desktop application.

Graph labels round rates; scientific data retains precision. Reports include
indexed complexes, original/augmented ODEs, auxiliary definitions, and warnings.
An open **ODEs under consideration** panel displays the original and augmented
systems directly. Reaction-file inputs display the ODEs implied by their
stoichiometry and supplied kinetics. These equations also appear in the full
report and text download; deriving them does not change the network.
Scientific limitations of selected or augmented realizations remain unchanged.

## Deployment

For a detailed inventory suitable for the IT team, see
[Web_Deployment_Handoff.txt](Web_Deployment_Handoff.txt).
It distinguishes the observed development environment from the proposed
production container and lists infrastructure/security decisions still needed.
Its scope is the IT team hosting and operating the web service only.

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
than the 60-second analysis budget. Do not log request bodies. No hosting
account is created or service published by this local implementation.

### Managed Docker hosting

Commit and push the intended `web_app` changes first. On a service such as
Render, create a **Web Service**, connect the repository, and choose Docker.

| Setting | Value |
|---|---|
| Git branch | `web_app` |
| Root / Docker build context | Repository root |
| Dockerfile path | `Dockerfile.web` |
| Health-check path | `/healthz` |
| Port environment variable | `PORT=8050` |
| Start command | Default Dockerfile command (`web.wsgi:server` via Gunicorn) |

The current command binds to `0.0.0.0:8050`; it does not read `PORT` dynamically.
Setting `PORT=8050` aligns Render's configuration with that command. If a host
requires another port, override the Docker command to bind Gunicorn to that
port, keeping two synchronous workers and a timeout above 60 seconds.

Deploy and open the provider's assigned HTTPS URL. Approximately 2 GB RAM is a
starting sizing estimate, not a guarantee: measure representative symbolic
workloads and concurrent use before choosing production capacity. No database
or persistent storage is needed for the current workflow.

Consult [Render Docker deployment](https://render.com/docs/docker) and
[Render web-service configuration](https://render.com/docs/web-services).
Do not use static hosting such as GitHub Pages for this Python backend.

### University or private server

Use a Linux server with Docker installed. Clone the repository and, from its
root, run:

```bash
git switch web_app
docker build -f Dockerfile.web -t crntanalysis-web .
docker run -d \
  --name crntanalysis-web \
  --restart unless-stopped \
  --memory=2g \
  --cpus=2 \
  -p 127.0.0.1:8050:8050 \
  crntanalysis-web
curl --fail http://127.0.0.1:8050/healthz
```

The health endpoint should return `{"status":"ok"}`. Keep the application port
bound to loopback instead of exposing Gunicorn directly. Install/configure an
HTTPS reverse proxy on the host. For Caddy, an example Caddyfile is:

```caddyfile
crnt.your-university.edu {
    reverse_proxy 127.0.0.1:8050
}
```

Replace the example domain, configure DNS to point to the server, and allow
the necessary reverse-proxy traffic through the firewall. Certificate issuance
needs appropriate DNS/network access. See [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https).
This minimal proxy example does **not** add authentication or rate limiting.
If the proxy is itself containerized, its loopback is different: connect it to
the app using a private Docker network rather than this host-only example.

For unpublished research, prefer an institution-controlled server when available.

### Pre-launch verification and operations

- Configure institutional authentication, an authenticated proxy, or VPN access
  for collaborator-only use. The app itself has no login; HTTPS is not access control.
- Add request-rate limits and retain resource limits. Keep server/proxy timeouts
  longer than the 60-second calculation budget (Gunicorn currently uses 90 seconds).
- Confirm the deployed image contains no private research inputs or reports;
  ensure application and proxy logs do not record request bodies.
- Test `/healthz`, reaction and ODE uploads, auxiliary/fractional options,
  graph interaction, ODE display, PNG export, and report downloads over HTTPS.
- Monitor memory, CPU, worker timeouts, and failures under expected concurrency.
  Health checks verify that the web process is alive, not scientific correctness.
- Keep dependency security updates and a rollback plan for deployed versions.

Useful private-server commands:

```bash
docker logs --tail 100 crntanalysis-web
docker stats --no-stream crntanalysis-web
docker stop crntanalysis-web
docker start crntanalysis-web
```

Running the launch command again with the same container name will fail while
that container exists. For an update, build a new versioned image and plan a
controlled container replacement; do not overwrite a running release blindly.
Docker deployment has to be verified on the intended server; these instructions
are not evidence of an already hosted or production-certified service.

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
- Default analysis limits: 1 MiB model input, 60 seconds per analysis, 10000 complexes, 50000
  reactions, and 8 MiB serialized results. HTTP bodies default to 24 MiB to
  accommodate bounded result state sent back to graph callbacks.
- Linux analysis children have a 1 GiB address-space ceiling. Other operating
  systems retain the timeout but need deployment-level memory controls.
- Child processes are terminated and reaped after completion, failure, or timeout.
  Synchronous Gunicorn workers bound concurrent requests per instance.
- These controls are not a full hostile-code sandbox or DDoS defense. Public
  deployment needs operational hardening, dependency auditing, and version pins.

This version does not include logins, saved-project accounts, collaborative
editing, or retained server-side reports. Networks beyond the deployment's
configured budget can still use an appropriately provisioned Python workflow.
Web build requirements use compatible ranges, not a lockfile.

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

## Larger models and deployment settings

Set these environment variables before starting the web server, then restart
all workers. Limits apply to pasted text and uploads of every supported extension.

| Environment variable | Default | Purpose |
|---|---|---|
| `CRNT_WEB_MAX_INPUT_BYTES` | `1048576` | Decoded UTF-8 model limit (1 MiB). |
| `CRNT_WEB_MAX_RESULT_BYTES` | `8388608` | Serialized result limit (8 MiB). |
| `CRNT_WEB_MAX_COMPLEXES` | `10000` | Full calculation network-complex limit. |
| `CRNT_WEB_MAX_REACTIONS` | `50000` | Full calculation network-reaction limit. |
| `CRNT_WEB_MAX_RENDER_COMPLEXES` | `300` | Complexes per browser graph page. |
| `CRNT_WEB_MAX_RENDER_REACTIONS` | `1000` | Rendered edges per graph page. |
| `CRNT_WEB_TIMEOUT_SECONDS` | `60` | Analysis wall-clock budget. |
| `CRNT_WEB_MEMORY_MB` | `1024` | Per-child Linux address-space ceiling, in MiB; provision container headroom separately. |
| `CRNT_WEB_MAX_REQUEST_BYTES` | automatic | HTTP request limit; at least max(8 x input limit, 3 x result limit). |

Example (macOS/Linux):

```bash
CRNT_WEB_MAX_INPUT_BYTES=10485760 python -m web.app
```

For Docker add `-e CRNT_WEB_MAX_INPUT_BYTES=10485760` before the image name;
managed hosts can set the same value in their environment settings. The
HTTP limit automatically scales for base64/JSON and result callback overhead.
Match the reverse proxy/platform body-size limits as well. Invalid or undersized
settings fail at startup instead of silently discarding larger requests.

For longer calculations, also increase Gunicorn's 90-second timeout and proxy
timeouts beyond the chosen analysis timeout. Input size alone does not measure
complexity: adjacency is automatically sparse above 256 complexes, and rank
uses exact sparse domain elimination on linkage-class complex differences.
Do not explicitly densify large matrices. Symbolic rank can still be costly;
large reports/results and dense intermediate elimination can consume memory.
Raise analysis/result/time limits
only after benchmarking server memory, browser responsiveness, and concurrent
users. These changes do not provide unlimited-network support.

Sparse adjacency reports use a tagged object with `format: "sparse"`,
`shape: [n,n]`, and `entries: [[row,column,weight], ...]`. Absent cells mean
zero; row/column positions follow the serialized complexes list. Rate symbols,
reverse channels, and lists of parallel weights are preserved. Small networks
retain dense nested lists. Updated report readers accept both formats; older
versions may not read new sparse reports. Python matrix-style indexing remains
available without materializing zeros. See the scientific guide for exact-rank
methodology.

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
| `timeout` | `float` | deployment default (`60`) | Child-process wall-clock budget in seconds. |
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
def elements(self, payload, mode='reaction', linkage='all', page=1, focus=None)
def view(self, payload, mode='reaction', linkage='all', page=1, focus=None)
```

#### Parameters

| Name | Type | Default | Purpose |
|---|---|---|---|
| `payload` | `dict` or `None` | required | Serialized web result. |
| `mode` | `str` | `'reaction'` | Directed reactions or undirected linkage graph. |
| `linkage` | `str` | `'all'` | Linkage-class index or all classes. |
| `page` | `int` | `1` | Graph page (clamped to the selected view). |
| `focus` | `str` or `None` | `None` | Complex ID/index for a one-hop neighborhood. |

#### Returns

- `elements` (`list[dict]`): Cytoscape node and edge data, including details and colors.
- `view` (`tuple`): `elements`, explicit rendering-status message, and page count.

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
