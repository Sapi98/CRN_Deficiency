param(
    [ValidateSet("venv", "conda")]
    [string]$Environment
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not $Environment) {
    Write-Host "CRNTAnalysis automatic setup"
    Write-Host "You must already have either Python 3.9+ or Conda installed."
    Write-Host "You only need the prerequisite for the option you choose."
    Write-Host ""
    Write-Host "  1) Python virtual environment (requires Python 3.9+; recommended)"
    Write-Host "  2) Conda environment (requires Miniconda or Anaconda)"
    $Choice = Read-Host "Choose 1 or 2 [1]"
    if (-not $Choice -or $Choice -eq "1") {
        $Environment = "venv"
    } elseif ($Choice -eq "2") {
        $Environment = "conda"
    } else {
        Write-Error "Choose 1 or 2."
    }
}

if ($Environment -eq "venv") {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $PythonExe = "py"
        $PythonArgs = @("-3")
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $PythonExe = "python"
        $PythonArgs = @()
    } else {
        Write-Host "Python 3.9 or newer was not found."
        Write-Host "Install Python from https://www.python.org/downloads/ and run setup.bat again."
        exit 1
    }

    & $PythonExe @PythonArgs -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Python 3.9 or newer is required."
    }

    Write-Host "Creating the virtual environment in .venv ..."
    & $PythonExe @PythonArgs -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Could not create the virtual environment." }
    $VenvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    Write-Host "Installing CRNTAnalysis and its dependencies ..."
    & $VenvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "Could not upgrade pip." }
    & $VenvPython -m pip install $PSScriptRoot
    if ($LASTEXITCODE -ne 0) { throw "Could not install CRNTAnalysis." }

    Write-Host ""
    Write-Host "Setup complete."
    Write-Host ""
    Write-Host "Each time you open a new Command Prompt, go to this project folder and run:"
    Write-Host "  .venv\Scripts\activate.bat"
    Write-Host ""
    Write-Host "For PowerShell, activate with:"
    Write-Host "  .\.venv\Scripts\Activate.ps1"
    Write-Host ""
    Write-Host "Then launch the desktop application with:"
    Write-Host "  crntanalysis-gui"
    Write-Host ""
    Write-Host "Or analyze an example with:"
    Write-Host "  crntanalysis Example_Data\crn1.react"
    Write-Host ""
    Write-Host "When finished, leave the environment with:"
    Write-Host "  deactivate"
} else {
    if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
        Write-Host "Conda was not found. Install Miniconda or Anaconda, or rerun setup.bat and choose option 1."
        exit 1
    }
    & conda run --name crntanalysis python --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Reusing the existing Conda environment named crntanalysis."
    } else {
        Write-Host "Creating the Conda environment named crntanalysis ..."
        & conda create --name crntanalysis python=3.12 pip --yes
        if ($LASTEXITCODE -ne 0) { throw "Could not create the Conda environment." }
    }
    Write-Host "Installing CRNTAnalysis and its dependencies ..."
    & conda run --name crntanalysis python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "Could not upgrade pip in the Conda environment." }
    & conda run --name crntanalysis python -m pip install $PSScriptRoot
    if ($LASTEXITCODE -ne 0) { throw "Could not install CRNTAnalysis." }

    Write-Host ""
    Write-Host "Setup complete."
    Write-Host ""
    Write-Host "Each time you open a new terminal, activate the environment with:"
    Write-Host "  conda activate crntanalysis"
    Write-Host ""
    Write-Host "Then launch the desktop application with:"
    Write-Host "  crntanalysis-gui"
    Write-Host ""
    Write-Host "Or analyze an example with:"
    Write-Host "  crntanalysis Example_Data\crn1.react"
    Write-Host ""
    Write-Host "When finished, leave the environment with:"
    Write-Host "  conda deactivate"
}
