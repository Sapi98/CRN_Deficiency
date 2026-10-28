# Chemical Reaction Network Theory Analysis (CRNTAnalysis)

`crntanalysis` is a Python package for parsing chemical reaction networks,
constructing their complex graphs, and calculating standard Chemical Reaction
Network Theory (CRNT) deficiency. It accepts explicit reaction files and
mass-action polynomial ODE files, provides typed and dictionary APIs, and
includes a command-line analysis pipeline that writes structured reports.

The current application version is **v1.1** (package version `1.1.0`).

ODE formatting examples demonstrate three approaches:

| Approach | Example | Required options |
|---|---|---|
| Fully sectioned rational ODEs with explicit headings | `Example_Data/rational_auxiliary_sectioned.ode` | `--lift-rational` |
| XPP-style rational ODEs with a shared auxiliary | `Example_Data/rational_auxiliary_xpp.ode` | `--lift-rational` |
| Sectioned fractional-power ODEs with an auxiliary | `Example_Data/fractional_auxiliary.ode` | `--allow-fractional --lift-rational` |

## Table of contents

- [License](#license)
- [Citation](#citation)
- [Features](#features)
- [Requirements](#requirements)
- [Visualization](#visualization)
- [Installation](#installation)
  - [Automated setup (recommended)](#automated-setup-recommended)
  - [Standard installation](#standard-installation)
  - [Using `venv`](#using-venv)
  - [Using Conda](#using-conda)
  - [Using pyenv](#using-pyenv)
- [Desktop GUI](#desktop-gui)
  - [Editing the interface](#editing-the-interface)
- [Interactive web application](#interactive-web-application)
  - [Hosting the web application](#hosting-the-web-application)
- [Building a standalone executable](#building-a-standalone-executable)
  - [Build environment and commands](#build-environment-and-commands)
  - [Sharing the application](#sharing-the-application)
  - [Troubleshooting dependency installation](#troubleshooting-dependency-installation)
  - [Verify before sharing](#verify-before-sharing)
- [Quick start](#quick-start)
- [Input formats](#input-formats)
- [Command-line usage](#command-line-usage)
  - [Analyze reaction and ODE files](#analyze-reaction-and-ode-files)
  - [Analyze raw text or piped input](#analyze-raw-text-or-piped-input)
  - [Select how unresolved values are handled](#select-how-unresolved-values-are-handled)
  - [Control console and analysis-file output](#control-console-and-analysis-file-output)
  - [Generate reaction-network and linkage-graph figures](#generate-reaction-network-and-linkage-graph-figures)
  - [Interactive input](#interactive-input)
  - [Argument reference](#argument-reference)
- [Output](#output)
- [Project structure](#project-structure)
- [Testing](#testing)
- [Known limitations](#known-limitations)
- [Detailed Documentation](#detailed-documentation)

## License

This software is licensed under the
[PolyForm Noncommercial License 1.0.0](LICENSE). It may be used, modified, and
distributed for noncommercial purposes, including education and scientific
research. Commercial use requires a separate written license; contact
[Saptarshi Biswas](mailto:saptarshi.biswas9@gmail.com).

Required Notice: Copyright 2026 Saptarshi Biswas

## Citation

If you use CRNTAnalysis in your research, please cite the software. The
repository also includes machine-readable citation metadata in
[CITATION.cff](CITATION.cff).

Plain text:

> Biswas, Saptarshi (2026). *CRNTAnalysis: Chemical Reaction Network Theory
> Analysis* (version 1.1.0) [Software].
> https://github.com/Sapi98/CRN_Deficiency

BibTeX:

```bibtex
@software{biswas2026crntanalysis,
  author  = {Biswas, Saptarshi},
  title   = {CRNTAnalysis: Chemical Reaction Network Theory Analysis},
  year    = {2026},
  version = {1.1.0},
  url     = {https://github.com/Sapi98/CRN_Deficiency}
}
```

## Features

- Parse `.react` files into indexed complexes and directed reactions.
- Parse compatible mass-action `.ode` files into a canonical reaction-network
  realization.
- Preserve unresolved rate constants and stoichiometric coefficients as
  symbols, or apply strict/default-one policies.
- Build a directed complex graph and a weighted undirected adjacency matrix.
- Calculate whole-network and per-linkage-class deficiency.
- Calculate exact and generic symbolic stoichiometric ranks with SymPy.
- Analyze files or raw text through a reusable service layer.
- Print console summaries and write `.txt`, `.analysis`, or `.output` reports.

## Requirements

- Python 3.9 or newer
- SymPy 1.13 or newer and below version 2
- PySide6 6.5 or newer and below version 7 for the desktop GUI

Installing the project installs SymPy, PySide6, NetworkX, and Matplotlib
(which also installs NumPy). The root `requirements.txt` provides the same
application dependencies. Setuptools 61+ and wheel are declared as isolated
build requirements in `pyproject.toml`. Parsing and deficiency analysis use
SymPy; graph rendering uses NetworkX and Matplotlib.

## Visualization

Graph dependencies are included in the standard installation. The existing
visualization extra remains supported:

```bash
python -m pip install '.[visualization]'
```

```python
from crntanalysis import ReactionFileParser
from crntanalysis.visualization import NetworkVisualizer

network = ReactionFileParser().parse_file("Example_Data/crn1.react")
visualizer = NetworkVisualizer()
figure, axes = visualizer.draw_reaction_network(network, show_deficiency=True)
visualizer.save(figure, "output/reactions.svg")
figure, axes = visualizer.draw_linkage_graph(network, show_deficiency=True)
visualizer.save(figure, "output/linkages.png")
```

Nodes represent complexes, with the same indices used by the parser. Reactions
have directed arrows and numerical or symbolic rate labels. The linkage view
is undirected; connected components are colored and indexed as linkage classes.
Parallel reactions and self-loops are preserved. Deficiency labels involving
unresolved stoichiometry use the calculator's generic symbolic rank.

Both draw methods accept an existing Matplotlib `ax` for GUI embedding and a
`positions` mapping from complex index to `(x, y)` for custom layouts. They
return `(figure, axes)` without opening a window. To display interactively,
create axes with `matplotlib.pyplot.subplots()`, pass `ax=axes`, then call
`matplotlib.pyplot.show()`. PNG, SVG, and PDF export are supported.

`NetworkGraphAdapter` exposes NetworkX graphs for further customization.
The linkage graph retains all reactions on each undirected connection.

## Installation

### Automated setup (recommended)

The setup scripts create an isolated environment, install CRNTAnalysis and all
required packages, and then print the exact commands needed to activate the
environment and start the application. They offer a choice between a standard
Python virtual environment (recommended for most users) and Conda.

**Before running a setup script, install one of the following:**

- **Python 3.9 or newer** from [python.org](https://www.python.org/downloads/)
  to use the recommended virtual-environment option. On Windows, enable
  **Add Python to PATH** during installation.
- **Miniconda or Anaconda** from the
  [Conda installation guide](https://docs.conda.io/projects/conda/en/latest/user-guide/install/)
  to use the Conda option.

You only need Python or Conda, not both. The setup script checks the selected
prerequisite and displays a helpful message if it cannot find it.

On **macOS or Linux**, open Terminal in the project folder and run:

```bash
bash setup.sh
```

On **Windows**, double-click `setup.bat`, or open Command Prompt in the project
folder and run:

```bat
setup.bat
```

Choose option `1` for the recommended `.venv` setup or option `2` for a Conda
environment named `crntanalysis`.

Advanced users can skip the question with `bash setup.sh --venv` or
`bash setup.sh --conda` on macOS/Linux, and `setup.bat venv` or
`setup.bat conda` on Windows. Existing environments are reused and updated.

### Standard installation

Install from the repository root into the active Python environment:

```bash
python3 -m pip install .
```

After installation, launch the desktop interface with `crntanalysis-gui` or use
`crntanalysis` for the command-line interface. The GUI layout is included in
the installed package, so launching does not require the repository directory.

For editable development:

```bash
python3 -m pip install -e .
```

### Using `venv`

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install .
```

Use `python -m pip install -e .` on the last line for an editable development
installation. Run `deactivate` to leave the environment.

### Using Conda

```bash
conda create --name crntanalysis python=3.12 pip
conda activate crntanalysis
python -m pip install .
```

Although Conda creates and manages the environment, pip installs this local
package and its declared Python dependencies inside that environment.

### Using pyenv

Select an isolated Python version with pyenv:

```bash
pyenv install 3.12.4
pyenv local 3.12.4
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install .
```

If the optional `pyenv-virtualenv` plugin is installed, it can replace the
`venv` steps:

```bash
pyenv virtualenv 3.12.4 crntanalysis
pyenv local crntanalysis
python -m pip install .
```

After installation, verify the package:

```bash
python3 -c "import crntanalysis; print(crntanalysis.__version__)"
```

## Desktop GUI

For a standalone app that collaborators can run without installing Python,
see [Building a standalone executable](#building-a-standalone-executable). The isolated build
workflow does not modify the development GUI or parser sources and creates
no installer.

The PySide6 desktop interface accepts pasted reaction/ODE text and model files
through drag and drop or a native file browser. Select the matching format and
click **Analyze model** to run the backend analysis service. The overview shows
network deficiency, complexes, linkage classes, stoichiometric rank, species,
and reactions. A read-only report includes per-linkage-class results, parser
warnings, and symbolic-rank notes. Missing parameter values remain symbolic.

You can open a saved `.analysis` or `.output` report immediately using
**Open result…** at the top of Analysis overview or **File → Open result…**
(Ctrl+O / Command+O). No model input or analysis run is required.

For ODE models, the input panel also provides **Allow fractional ODE powers**
and **Lift rational ODE rates using auxiliary species**. Enable both before
analyzing `Example_Data/fractional_auxiliary.ode`: its `y^1.5` term requires fractional
powers, and its `Auxiliary Species` section requires rational lifting.
These options are off by default and disabled for reaction-file inputs.
Deficiency then describes the augmented real-complex realization, not a
unique network determined by the original ODE.

The **Reaction graph** tab shows complexes as labeled nodes with directed
reaction arrows and rate labels. The **Linkage graph** tab shows undirected
connections between complexes. Both views color complexes by linkage class
and show each class’s deficiency in the legend. Graphs render when selected;
hovering a node adds an animated glow. Click a node to open a floating panel
with its composition, linkage class, deficiency, and connected reactions. The
panel stays on the clicked node when hovering others; click empty space or
press Esc to close it. The result and input
tabs use a light background and crisp blue text on hover. The toolbar supports pan, zoom, reset, and saving figures (including PNG, SVG,
and PDF). Editing the input clears the previous graphs along with the report.

Analysis runs in a background thread; input controls are disabled until it
finishes. Errors appear in the results area, and changing the input clears the
previous results. After a successful analysis, the GUI asks whether to save the
summary. The save dialog supplies a default filename and lets you choose the
destination and `.txt`, `.analysis`, or `.output` format. Plain-text files hold
the readable summary; the two structured formats preserve the complete network
and can be reopened with **Open result…** to restore the report and graphs.

From the repository root:

```bash
python3 -m pip install -r requirements.txt
python3 GUI/mainwindow.py
```

### Editing the interface

`form.ui` is the single source for the layout, styling, labels, and widgets.
Edit it in Qt Creator / Qt Designer, save, then launch `mainwindow.py` again.
At startup, the app automatically regenerates `ui_form.py` using the active
Python environment's PySide6 compiler and calls `Ui_MainWindow.setupUi()`.
No manual generation command is required. Changes appear on the next launch;
an already open window does not reload automatically.

`ui_form.py` is generated code; do not edit it by hand. `mainwindow.py` contains
startup and behavior (examples, file input, background analysis, and results).
Keep the existing interactive widgets' object names when editing the design:
`formatCombo`, `modelEditor`, `inputTabs`, `characterCount`, `exampleButton`,
`clearButton`, `browseButton`, `removeButton`, `fileLabel`, `dropZone`, and
`statusLabel`, `analyzeButton`, `resultsEmptyTitle`, `resultsMetrics`,
`resultsHint`, `openResultButton`, `saveResultButton`, `resultReport`,
`analysisTabs`, `reactionGraphLayout`,
`linkageGraphLayout`, `reactionGraphHint`, and `linkageGraphHint`. Layout, text, size, color, and position changes
need no Python edits. The graph pages’ **font → bold** property controls the
rendered graph text weight, and the graph hint labels hold the interaction
guidance displayed in the app.
New controls that need application behavior require signal connections in Python
or Designer. The Clear connection is already stored in `form.ui`.

Both `python GUI/mainwindow.py` from the repository root and
`python mainwindow.py` from inside `GUI` work. For an installed version, use
`crntanalysis-gui`. If the installed GUI directory is read-only, the generated
interface is loaded in memory instead of writing `ui_form.py`.

## Interactive web application

The `web_app` branch includes a Python Dash workspace with interactive reaction
and linkage graphs: drag nodes, pan/zoom, change layouts, filter linkage classes,
search complexes, inspect nodes/edges, and export PNG images. Upload or paste
models, inspect ODEs and deficiency results, and download reports. The web app
calls the same scientific service as the CLI and desktop GUI.

```bash
python3 -m venv .venv-web
source .venv-web/bin/activate
python -m pip install -r requirements-web.txt
python -m web.app
```

Open **http://127.0.0.1:8050**. On Windows, activate with
`.venv-web\Scripts\activate.bat` or `.venv-web\Scripts\Activate.ps1` instead.
The separate web environment needs no Qt installation. Existing desktop and
standalone workflows are unchanged.
The top-level `web/` app is excluded from pip distributions; run it from a
repository checkout. Installing `crntanalysis` does not install the web app.
Model uploads/pasted text support up to 1 MiB by default. Hosts can increase
this with `CRNT_WEB_MAX_INPUT_BYTES` before startup; see the
[larger-model settings](Documentation/web_app.md#larger-models-and-deployment-settings)
for graph/result limits, timeouts, and server-capacity considerations.
Large networks use sparse adjacency and exact sparse stoichiometric rank.
The default analysis budget is 10,000 complexes / 50,000 reactions / 60 seconds;
browser diagrams are paged separately (300 complexes / 1,000 edges per page).
Use graph pages, linkage filters, or a complex neighborhood to explore larger
systems. Full reports/downloads retain every accepted reaction; PNG exports
show only the current graph view. Large structured reports use a tagged sparse
adjacency object instead of a dense nested list and require an updated reader.

See [the web application guide](Documentation/web_app.md) for Docker deployment,
privacy, interaction details, resource limits, and tests. This implementation
is local, not publicly hosted; configure HTTPS and authentication before
sharing an internet-facing deployment.

### Hosting the web application

For an institutional software/security review, share the self-contained
[Web deployment handoff (TXT)](Documentation/Web_Deployment_Handoff.txt).
It lists direct and transitive Python packages, observed versions, browser
libraries, server requirements, data handling, limits, and approval checks.
The handoff requests hosting/operations for the web app only, not desktop
distribution or Python package publishing.

Host the repository application as a Python/Docker web service, not a static
website (GitHub Pages cannot run this backend). No C# conversion or executable
build is needed. Commit and push the intended changes to `web_app` before
deploying from Git.

**Managed hosting (for example, Render):** connect the repository as a Docker
web service and configure:

| Setting | Value |
|---|---|
| Branch | `web_app` |
| Root / build context | Repository root |
| Dockerfile | `Dockerfile.web` |
| Health-check path | `/healthz` |
| Environment variable | `PORT=8050` (matches the current Docker command) |

Use the default command from the Dockerfile. Deploy, then test the assigned
HTTPS URL. Start with approximately 2 GB RAM and measure actual usage with
representative models; this is a sizing estimate, not a capacity guarantee.
See [Render's Docker guide](https://render.com/docs/docker) and
[web-service configuration](https://render.com/docs/web-services).

**University or private Linux server:** install Docker, clone the repository,
and run from its root:

```bash
git switch web_app
docker build -f Dockerfile.web -t crntanalysis-web .
docker run -d --name crntanalysis-web --restart unless-stopped \
  --memory=2g --cpus=2 -p 127.0.0.1:8050:8050 crntanalysis-web
curl --fail http://127.0.0.1:8050/healthz
```

Keep port 8050 local to the server. Put an HTTPS reverse proxy in front of it;
for example, when Caddy runs on the same host, use:

```caddyfile
crnt.your-university.edu {
    reverse_proxy 127.0.0.1:8050
}
```

Replace the domain with yours, point its DNS to the server, and configure the
firewall for the reverse proxy. Caddy can provision HTTPS when its domain and
network prerequisites are met; see [automatic HTTPS](https://caddyserver.com/docs/automatic-https).

**Before sharing:** the app has no built-in login. For collaborator-only access,
configure institutional sign-in, an authenticated proxy, or VPN access. Add
rate limits, retain CPU/memory and calculation-time limits, avoid request-body
logging, and test uploads, graph interactions, downloads, and health checks.
HTTPS alone does not restrict who can use the app. A university-controlled
server is preferable for unpublished models when available.

See the [detailed deployment guide](Documentation/web_app.md#deployment) for
operations, troubleshooting, and verification. These instructions do not
publish or provision a server automatically.

## Building a standalone executable

This workflow keeps the Python package, CLI, GUI launcher, and development
Designer regeneration unchanged. It copies application sources into a temporary
directory, generates the UI there, and builds a standalone one-folder bundle.
The bundled GUI imports that generated UI without invoking Python subprocesses.
Only the three allowlisted public examples and project license are included;
research inputs and analysis outputs are not copied.

### Build environment and commands

Use a dedicated environment on the operating system and architecture you want
to distribute for. Collaborators do not need Python, but the build machine does.

```bash
python3 -m venv .venv-build
```

Activate with `source .venv-build/bin/activate` on macOS/Linux, or
`.venv-build\Scripts\activate` in Windows Command Prompt. Then, from the root:

```bash
python -m pip install --upgrade pip
python -m pip install --no-compile -r packaging/requirements-build.txt
python -m pip check
python packaging/build_standalone.py
```

### Sharing the application

Build separately on each target operating system; a macOS build does not
produce a Windows executable.

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

### Troubleshooting dependency installation

The `--no-compile` option skips installation-time bytecode compilation, not
the later PyInstaller build. It avoids trying to compile PySide6 template
files such as `__init__.tmpl.py`, which contain template syntax rather than
ordinary Python code.

If an installation was interrupted by a template `SyntaxError` followed by
a `TypeError`, some dependencies may be missing. With the build environment
activated, repair the installation:

```bash
python -m pip install --no-compile --force-reinstall -r packaging/requirements-build.txt
python -m pip check
python packaging/build_standalone.py
```

No application files or existing development environment need to be changed.
If downloads fail, resolve network access before building. On Windows, use
`python -m venv .venv-build` if `python3` is not available, and activate with
`.venv-build\Scripts\Activate.ps1` in PowerShell.

### Verify before sharing

Test on a clean machine without Python or this repository installed:

1. Open the app and verify the version label.
2. Analyze a reaction file and each supplied ODE example with its stated options.
3. Inspect both graphs and auxiliary ODEs in the report.
4. Save text and structured reports to a user-selected directory and reopen them.
5. Check the bundle contains no research files or generated research reports.

Unsigned applications may trigger operating-system warnings. Signing and macOS
notarization are separate release steps. Include project and dependency license
notices as required before distribution; freezing does not remove those obligations.

## Quick start

Parse a reaction file and calculate its deficiency:

```python
from crntanalysis import ReactionFileParser, calculate_deficiency

network = ReactionFileParser().parse_file("Example_Data/crn1.react")
result = calculate_deficiency(network)

print(f"n = {result.number_of_complexes}")
print(f"s = {result.stoichiometric_rank}")
print(f"l = {result.number_of_linkage_classes}")
print(f"deficiency = {result.deficiency}")

for linkage_class in result.linkage_classes:
    print(linkage_class.complex_indices, linkage_class.deficiency)
```

For `Example_Data/crn1.react`, the whole-network result is `n=11`, `s=4`,
`l=5`, and deficiency `2`.

Parse a mass-action ODE model:

```python
from crntanalysis import ODEFileParser, calculate_deficiency

parsed = ODEFileParser().parse_file("model.ode")
network = parsed.network
result = calculate_deficiency(network)
```

Dictionary-returning convenience functions are also available:

```python
from crntanalysis import parse_ode_file, parse_reaction_file

reaction_data = parse_reaction_file("model.react")
ode_data = parse_ode_file("model.ode")
```

## Input formats

Declare original dynamic variables explicitly in a sectioned ODE file:

```text
Species:
x, y

ODE Model:
dx/dt = -k*x
dy/dt = k*x

Coefficients:
k = 0.5
```

Every declared species must have exactly one derivative equation (use `0`
if its derivative is zero). All other expression identifiers are constant
parameters unless defined as auxiliary species. Numeric values go in
`Coefficients:`; unspecified constants follow the selected unresolved-value
policy. Declared names determine species capitalization. Auxiliary species
belong in `Auxiliary Species:`, not in the original `Species:` list, because
their ODEs are derived automatically. For backward compatibility, omitted
species declarations still infer dynamic species from derivative left sides.

For XPP-style input, use the tool extension `species x, y` before the equations.
This declaration is a CRNTAnalysis extension, not a claim of standard XPP syntax.

XPP-style `.ode` files can be read directly, without converting them to the
section format. This reader uses numeric parameter declarations and autonomous
derivative equations, for example:

```text
param k=2, q=0.5
x' = -k*x
dy/dt = k*x-q*y
init x=1,y=0
@ total=250,dt=0.1
done
```

`p`, `par`, `param`, `parameter`, and `parameters` are supported parameter
keywords. Both derivative spellings are accepted, as are `#` comments,
scientific notation, and backslash line continuations. Initial-state, solver,
and plotting directives are ignored in this format: only parameters and
equations enter structural analysis. Without initial conditions, reciprocal
lifting records the required auxiliary initial-value expression as a warning.
The existing section format continues to support explicit `Initial Conditions`.

Run the generic XPP-style example directly:

```bash
crntanalysis "Example_Data/rational_auxiliary_xpp.ode" --lift-rational
```

Raw XPP-style equation text is also automatically recognized through `--text`,
`--stdin`, and the analysis service. Rational kinetics still requires
`--lift-rational`, and fractional powers require `--allow-fractional`.
The reader supports the parameter/equation subset of the
[XPP file format](https://sites.pitt.edu/~phase/bard/bardware/xpp/help/xppodes.html),
not its full language. Standalone assignments such as `s = 1/(1+x)` are
treated as named reciprocal auxiliary species with `--lift-rational`, not
as general XPP fixed variables. Explicit polynomial auxiliary definitions
are also supported. Each auxiliary adds its chain-rule ODE to the augmented
system. Definitions can depend on other auxiliaries and may appear in any
order, for example:

```text
ODE Model:
dx/dt = -x*t

Auxiliary Species:
s = 1/(1+x)
t = 1/(1+s)

Initial Conditions:
x = 1
```

With rational lifting enabled, this adds `ds/dt = x*t*s^2` and
`dt/dt = -x*s^2*t^3` (the second `t` is the species name), and computes
consistent auxiliary initial values. Circular definitions such as
`s = 1/(1+t)` together with `t = 1/(1+s)` are rejected: they require an
implicit/DAE formulation rather than explicit chain-rule substitution.
An augmented system must still admit a nonnegative-complex CRN realization;
adding auxiliaries does not guarantee this.

ODE-generated reactions with identical source and target complexes are merged
into one directed edge by adding their rate constants. This is valid because
these canonical reactions share the source-complex kinetic monomial. Symbolic
rates remain symbolic sums; reverse reactions remain separate. Explicit
reaction-file channels are retained as written.

Console, GUI, and saved plain-text reports include indexed complexes, reactions
and rates, species lists, parameters, initial conditions, the original ODEs,
and the complete augmented ODE system. Auxiliary details include each
definition, derived ODE, dependency information when available, constraints,
domain, and initial value. Structured `.analysis` and `.output` files retain
this information in network metadata and restore the detailed report when opened.
Human-readable reports use `^` for powers (for example, `x^2` and `y^(7/5)`).
Structured reports retain Python/SymPy `**` notation for reliable computation.

Functions, other fixed variables, events, delayed,
stochastic, integral, and difference equations require explicit conversion.

A reaction file contains labeled sections such as:

```text
Reactions:
2 X + Y k1-> 3 X

Rate Constants:
k1 = 0.5

Initial Conditions:
X = 1.0
Y = 2.0
```

An ODE file contains polynomial mass-action equations:

```text
ODE Model:
dx/dt = k1 * X^2 * Y
dy/dt = -k1 * X^2 * Y

Coefficients:
k1 = 0.5
```

The ODE parser expands parentheses and combines repeated species factors.
For example, `x*(1-x/K)`, `x-(1/K)*x^2`, and `x-(1/K)*x*x` give the same
canonical realization: `x -> 2 x` at rate `1` and `2 x -> x` at rate `1/K`.
Numeric coefficients and species-independent parameter expressions are valid
effective rates. Define `K` in the `Coefficients` section to resolve `1/K`;
otherwise it remains symbolic under the default policy. Every species must
have a derivative equation; use `dy/dt = 0` for an unchanged species.

The default ODE mode requires ordinary polynomial mass-action kinetics.
Two opt-in extensions support real powers and reciprocal auxiliary species:

```bash
crntanalysis Example_Data/fractional_auxiliary.ode --allow-fractional --lift-rational
```

`--allow-fractional` uses nonnegative real kinetic powers as the coefficients
of the inferred source complex. For example, `-k*y^1.4` gives
`1.4 y -> 0.4 y`, with rate `k*y^1.4`. This is a selected real-complex
realization, not a uniquely inferred physical reaction mechanism.

`--lift-rational` introduces a reciprocal species for each distinct
species-dependent polynomial denominator, reuses shared denominators, and
derives its ODE by the chain rule. To choose its name, add:

```text
Auxiliary Species:
s = 1/(1+x)
```

Without this section, names such as `_aux_s1` are generated without conflicting
with model identifiers. Parameters are treated as constant. The original
equations, augmented equations, constraints, domain restrictions, and derived
initial values are stored in the structured report's `analysis_metadata`.
For the fractional auxiliary example, `s(0) = 1/(1+1) = 0.5`. Equivalence holds on the constraint
`s*(1+x)=1` where the denominator is positive. An arbitrary initial value
for `s` defines a different dynamical system.

The reported deficiency belongs to the augmented realization. Lifting does not
guarantee a kinetic realization: negative product coefficients, unresolved
exponents requiring arithmetic, nonpolynomial denominators, and unsupported
denominator powers still produce errors. Classical mass-action deficiency
theorems are not automatically asserted for real-complex or general kinetics.

The equivalent Python API is:

```python
parsed = ODEFileParser(allow_fractional=True, lift_rational=True).parse_file(
    "Example_Data/fractional_auxiliary.ode"
)
print(parsed.network.analysis_metadata["auxiliary_species"])
```

For an explicitly declared reaction network, kinetics can instead be specified
independently of stoichiometry. Fractional complex coefficients are already
supported by the reaction parser:

```text
Reactions:
Y k-> 0
Rate Constants:
k = 2
Kinetic Orders:
k = 1.4 Y
```

This keeps the source complex `Y` while assigning rate `k*Y^1.4`. Alternatively,
use a `Rate Laws` section, e.g. `k = k*X*Y/(1+X+a*z)`, with the corresponding
stoichiometric reaction explicitly declared. Each label can have kinetic orders
or a full rate law; full laws are authoritative expressions, and their domain
and nonnegativity must be established by the model author. Every reaction with
the same label receives the same kinetic declaration. Graph weights remain
rate constants or labels, not concentration-dependent rates.

Unspecified values remain symbolic by default. Alternative policies are:

```python
ReactionFileParser(unresolved="symbolic")  # Default
ReactionFileParser(unresolved="error")     # Require every value
ReactionFileParser(unresolved="one")       # Substitute 1.0
```

See [Scientific methods](Documentation/scientific_methods.md) for the precise
CRNT interpretation, ODE realization rules, adjacency semantics, and symbolic
rank limitations.

Additional valid examples are available in `Example_Data/`:

- `reversible_conversion.react` — a reversible two-complex reaction.
- `enzyme_binding.react` — reversible enzyme binding followed by product formation.
- `reversible_conversion.ode` — a reversible conversion expressed as ODEs.
- `linear_pathway.ode` — a three-species linear mass-action pathway.

`crn2.ode` is intentionally invalid and demonstrates rejection of a model that
cannot be represented as an ordinary mass-action reaction network.

## Command-line usage

Installing the package creates the `crntanalysis` command. Display every
available argument with:

```bash
crntanalysis --help
```

The general form is:

```text
crntanalysis [INPUT_FILE | --file PATH | --text MODEL | --stdin] [OPTIONS]
```

Exactly one input source may be supplied. When no input source is given, the
application starts its interactive prompt.

### Analyze reaction and ODE files

The input format is inferred from a `.react` or `.ode` filename:

```bash
crntanalysis Example_Data/crn1.react
crntanalysis Example_Data/crn2.ode
crntanalysis --file Example_Data/crn1.react
```

By default, this prints a summary and creates
`output/crn1_analysis.analysis`. Use `--format` when the filename does not have
a recognized extension:

```bash
crntanalysis model.txt --format react
crntanalysis equations.txt --format ode
```

### Analyze raw text or piped input

Pass a complete model directly. ANSI-C quoting (`$'...'`) is supported by Bash
and Zsh:

```bash
crntanalysis --format react --text $'Reactions:\nA k1-> B'
```

Pipe a document through standard input with `--stdin`:

```bash
crntanalysis --stdin < Example_Data/crn1.react
printf 'Reactions:\nA k1-> B\n' | crntanalysis --stdin --format react
```

PowerShell users can pipe a here-string:

```powershell
@"
Reactions:
A k1-> B
"@ | crntanalysis --stdin --format react
```

### Select how unresolved values are handled

Missing rate constants and stoichiometric coefficients remain symbolic by
default. The other policies either reject them or substitute `1.0`:

```bash
crntanalysis model.react --unresolved symbolic
crntanalysis model.react --unresolved error
crntanalysis model.react --unresolved one
```

### Control console and analysis-file output

Choose the output folder, basename, and `.txt`, `.analysis`, or `.output`
extension:

```bash
crntanalysis model.react \
  --output-dir reports \
  --output-name experiment_01 \
  --extension output
```

The `.analysis` and `.output` extensions contain structured JSON; `.txt`
contains the human-readable summary. Use `--no-file` for console output only,
or `--no-console` for a file-oriented batch run:

```bash
crntanalysis model.react --no-file
crntanalysis model.react --no-console
```

### Generate reaction-network and linkage-graph figures

Install visualization support first:

```bash
python -m pip install '.[visualization]'
```

Generate both figures using automatic filenames under `output/`:

```bash
crntanalysis model.react --reaction-graph --linkage-graph
```

For `model.react`, this creates
`output/model_analysis_reaction_graph.png` and
`output/model_analysis_linkage_graph.png`, along with the analysis report.
Choose SVG or PDF for generated paths and include per-linkage deficiencies:

```bash
crntanalysis model.react \
  --reaction-graph \
  --linkage-graph \
  --graph-format svg \
  --show-linkage-deficiency
```

An explicit path after either graph argument overrides the generated path and
determines that figure's format:

```bash
crntanalysis model.react \
  --reaction-graph figures/reactions.pdf \
  --linkage-graph figures/linkages.svg \
  --graph-dpi 300 \
  --layout-seed 7
```

Reaction labels are displayed on the directed graph by default. They can be
hidden there or enabled on the undirected linkage graph:

```bash
crntanalysis model.react --reaction-graph --no-rate-labels
crntanalysis model.react --linkage-graph --show-linkage-rates
```

For a figure-only batch operation:

```bash
crntanalysis model.react \
  --reaction-graph \
  --linkage-graph \
  --no-file \
  --no-console
```

### Interactive input

Run `crntanalysis` without an input argument to enter a file path or paste a
complete model. When pasting, enter `END` on a line by itself:

```bash
crntanalysis --format react --unresolved symbolic
```

### Argument reference

| Argument | Purpose | Default |
|---|---|---|
| `INPUT_FILE` | Read a `.react` or `.ode` document from a file. | Interactive input |
| `--file PATH` | Read a file using an explicit named argument. | — |
| `--text MODEL` | Read the complete model from one command-line string. | — |
| `--stdin` | Read the complete model from standard input. | — |
| `--format {auto,react,ode}` | Select or infer the input format. | `auto` |
| `--unresolved {symbolic,error,one}` | Handle missing parameter values. | `symbolic` |
| `--allow-fractional` | Infer ODE source complexes with nonnegative real powers. | Disabled |
| `--lift-rational` | Introduce reciprocal species and derive auxiliary ODEs. | Disabled |
| `--output-dir DIRECTORY` | Set the report and automatic-figure directory. | `output` |
| `--output-name NAME` | Set the report and automatic-graph basename. | Source-derived |
| `--extension {analysis,output,txt}` | Select structured JSON or plain-text summary output. | `analysis` |
| `--no-file` | Skip the structured analysis file. | File enabled |
| `--no-console` | Skip the human-readable analysis summary. | Summary enabled |
| `--reaction-graph [PATH]` | Generate a directed reaction graph. | Disabled |
| `--linkage-graph [PATH]` | Generate an undirected linkage graph. | Disabled |
| `--graph-format {png,svg,pdf}` | Format automatic graph filenames. | `png` |
| `--graph-dpi DPI` | Set raster export resolution; must be positive. | `150` |
| `--layout-seed SEED` | Make automatic graph placement reproducible. | `42` |
| `--no-rate-labels` | Hide labels on the directed reaction graph. | Labels enabled |
| `--show-linkage-rates` | Show reaction/rate labels on the linkage graph. | Labels disabled |
| `--show-linkage-deficiency` | Add per-class deficiencies to graph legends. | Disabled |

For GUI or application integration, use the console-independent service:

```python
from crntanalysis.orchestrator import AnalysisReportWriter, CRNAnalysisService

service = CRNAnalysisService()
outcome = service.analyze_file("model.react")
# outcome = service.analyze_text(editor_text, input_format="react")

AnalysisReportWriter().write(outcome, "output")
```

## Output

`AnalysisOutcome` provides the parsed network, global and linkage-class
deficiencies, source metadata, and parser warnings. Structured `.analysis` and
`.output` reports use JSON and can be reopened in the GUI. `.txt` reports store
the same concise summary shown in the report pane but cannot restore graphs.

Complex compositions are stored once and indexed. Reactions refer to source
and target complex indices. An adjacency cell is `0` when no connection exists,
a number or symbol for one reaction path, and a list for parallel or reverse
paths.

## Project structure

```text
crntanalysis/              Installable Python package
Documentation/             Engineering and scientific documentation
Example_Data/              Example reaction and ODE inputs
GUI/                       Desktop GUI and Qt Designer layout
tests/                     Unit and GUI integration tests
README.md                  User overview and usage guide
requirements.txt           Runtime dependency list
pyproject.toml             Build-system and Qt project configuration
setup.py                   Package metadata and console entry point
setup.sh                   Automated macOS/Linux environment setup
setup.bat / setup.ps1      Automated Windows environment setup
```

For module responsibilities, architecture, extension points, packaging, and
release workflow, see [Developer and operations guide](Documentation/devops.md).

## Testing

Run the complete test suite from the repository root:

```bash
python3 -m unittest discover -s tests -v
```

The tests cover reaction parsing, ODE parsing and validation, symbolic values,
graph construction, weighted adjacency, deficiency calculation, orchestration,
and report writing.

## Known limitations

- ODE-to-network inversion is not unique; the ODE parser returns the canonical
  grouped realization documented in the scientific methods guide.
- ODEs that cannot represent an ordinary mass-action CRN are rejected.
- Symbolic rank is generic. Special parameter values may change the rank and
  deficiency.
- The [desktop GUI](#desktop-gui) supports analysis, text reports, and graph
  visualization. Structured report export is available through the Python API
  or command line.

## Detailed Documentation

- [Developer and operations guide](Documentation/devops.md)
- [Scientific methods](Documentation/scientific_methods.md)
