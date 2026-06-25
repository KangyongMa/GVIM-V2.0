$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BackendDir = Join-Path $ProjectRoot "backend"
$BackendVenvDir = Join-Path $BackendDir ".venv"
$BackendScriptsDir = Join-Path $BackendVenvDir "Scripts"
$BackendPythonRequest = if ($env:DEER_FLOW_BACKEND_PYTHON_VERSION) { $env:DEER_FLOW_BACKEND_PYTHON_VERSION } else { "3.12" }
$DefaultScienceRoot = Join-Path $ProjectRoot "..\..\gvim-science-skills-mcp"
$ScienceRoot = if ($env:GVIM_SCIENCE_ROOT) { $env:GVIM_SCIENCE_ROOT } else { $DefaultScienceRoot }
$ScienceRoot = if (Test-Path $ScienceRoot) { (Resolve-Path $ScienceRoot).Path } else { $null }

Set-Location $BackendDir

function Resolve-UvExecutable {
  $commands = @(Get-Command uv -All -ErrorAction SilentlyContinue)
  if (-not $commands) {
    throw "uv is required to run the DeerFlow backend. Install uv first, then rerun this script."
  }

  $nonConda = $commands |
    Where-Object { $_.Source -and ($_.Source -notmatch "\\(anaconda3|miniconda3|miniforge3|conda)\\|\\condabin\\") } |
    Select-Object -First 1
  if ($nonConda) {
    return $nonConda.Source
  }

  return ($commands | Select-Object -First 1).Source
}

$UvExe = Resolve-UvExecutable
Write-Host "[backend] uv $UvExe"

function Normalize-ExistingPath {
  param([Parameter(Mandatory = $true)][string]$Path)

  if (Test-Path -LiteralPath $Path) {
    return (Resolve-Path -LiteralPath $Path).Path.TrimEnd("\").ToLowerInvariant()
  }
  return $Path.TrimEnd("\").ToLowerInvariant()
}

function Get-PythonBasePrefix {
  param([Parameter(Mandatory = $true)][string]$PythonExe)

  if (-not (Test-Path -LiteralPath $PythonExe)) {
    return $null
  }

  $basePrefix = & $PythonExe -c "import sys; print(sys.base_prefix)" 2>$null
  if ($LASTEXITCODE -ne 0 -or -not $basePrefix) {
    return $null
  }
  return ($basePrefix | Select-Object -First 1).Trim()
}

function Get-PythonPrefix {
  param([Parameter(Mandatory = $true)][string]$PythonExe)

  $prefix = & $PythonExe -c "import sys; print(sys.prefix)" 2>$null
  if ($LASTEXITCODE -ne 0 -or -not $prefix) {
    return $null
  }
  return ($prefix | Select-Object -First 1).Trim()
}

function Get-ManagedPythonFromUvDir {
  param([Parameter(Mandatory = $true)][string]$VersionRequest)

  $uvPythonDir = (& $UvExe python dir 2>$null)
  if ($LASTEXITCODE -ne 0 -or -not $uvPythonDir) {
    return $null
  }

  $uvPythonDir = ($uvPythonDir | Select-Object -First 1).Trim()
  if (-not (Test-Path -LiteralPath $uvPythonDir)) {
    return $null
  }

  $versionPrefix = if ($VersionRequest -match "^(\d+\.\d+)") { $Matches[1] } else { $VersionRequest }
  $candidates = @()
  foreach ($dir in Get-ChildItem -LiteralPath $uvPythonDir -Directory -Filter "cpython-$versionPrefix.*-windows-x86_64-none" -ErrorAction SilentlyContinue) {
    if ($dir.Name -match "^cpython-(\d+\.\d+\.\d+)-windows-x86_64-none$") {
      $pythonExe = Join-Path $dir.FullName "python.exe"
      if (Test-Path -LiteralPath $pythonExe) {
        $candidates += [pscustomobject]@{
          Version = [Version]$Matches[1]
          Python = $pythonExe
        }
      }
    }
  }

  if (-not $candidates) {
    return $null
  }

  return ($candidates | Sort-Object Version -Descending | Select-Object -First 1).Python
}

function Resolve-ManagedBackendPython {
  param([Parameter(Mandatory = $true)][string]$VersionRequest)

  $pythonExe = Get-ManagedPythonFromUvDir $VersionRequest
  if ($pythonExe) {
    return $pythonExe
  }

  Write-Host "[backend] Installing uv-managed CPython $VersionRequest..."
  & $UvExe python install $VersionRequest
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }

  $pythonExe = Get-ManagedPythonFromUvDir $VersionRequest
  if (-not $pythonExe) {
    throw "Could not find a uv-managed CPython $VersionRequest after installation."
  }
  return $pythonExe
}

function Reset-BackendVenv {
  param([Parameter(Mandatory = $true)][string]$Reason)

  if (-not (Test-Path -LiteralPath $BackendVenvDir)) {
    return
  }

  $resolvedBackend = Normalize-ExistingPath $BackendDir
  $resolvedVenv = Normalize-ExistingPath $BackendVenvDir
  $expectedVenv = Normalize-ExistingPath (Join-Path $BackendDir ".venv")

  if ($resolvedVenv -ne $expectedVenv -or -not $resolvedVenv.StartsWith($resolvedBackend)) {
    throw "Refusing to remove unexpected virtualenv path: $BackendVenvDir"
  }

  Write-Host "[backend] Recreating backend\.venv ($Reason)..."
  Remove-Item -LiteralPath $BackendVenvDir -Recurse -Force
}

$BackendBasePython = Resolve-ManagedBackendPython $BackendPythonRequest
$BackendBasePrefix = Get-PythonPrefix $BackendBasePython
if (-not $BackendBasePrefix) {
  throw "Could not inspect backend Python: $BackendBasePython"
}

$ExistingVenvPython = Join-Path $BackendScriptsDir "python.exe"
$ExistingVenvBasePrefix = Get-PythonBasePrefix $ExistingVenvPython
if ($ExistingVenvBasePrefix -and ((Normalize-ExistingPath $ExistingVenvBasePrefix) -ne (Normalize-ExistingPath $BackendBasePrefix))) {
  Reset-BackendVenv "current interpreter base is $ExistingVenvBasePrefix, expected $BackendBasePrefix"
}

$env:PYTHONPATH = "."
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:DEER_FLOW_PROJECT_ROOT = $ProjectRoot
$env:DEER_FLOW_CONFIG_PATH = Join-Path $ProjectRoot "config.yaml"
$env:DEER_FLOW_EXTENSIONS_CONFIG_PATH = Join-Path $ProjectRoot "extensions_config.json"
$env:UV_PROJECT_ENVIRONMENT = $BackendVenvDir
$env:DEER_FLOW_BACKEND_VENV = $BackendVenvDir
$env:DEER_FLOW_BACKEND_PYTHON = Join-Path $BackendScriptsDir "python.exe"
$env:DEER_FLOW_COMMAND_VENV = $BackendVenvDir
$env:DEER_FLOW_COMMAND_PYTHON = $env:DEER_FLOW_BACKEND_PYTHON

function Test-PythonModules {
  param(
    [Parameter(Mandatory = $true)][string]$PythonExe,
    [Parameter(Mandatory = $true)][string[]]$Modules
  )

  $moduleList = ($Modules | ForEach-Object { "'$_'" }) -join ","
  & $PythonExe -c "import importlib.util, sys; missing=[m for m in [$moduleList] if importlib.util.find_spec(m) is None]; print(','.join(missing)); sys.exit(1 if missing else 0)"
  return $LASTEXITCODE -eq 0
}

function Ensure-NmrSkillRuntimeDeps {
  param([Parameter(Mandatory = $true)][string]$PythonExe)

  $nmrReq = Join-Path $ProjectRoot "skills\public\nmr-prediction\requirements.txt"
  $uniReq = Join-Path $ProjectRoot "skills\public\nmr-prediction\assets\Uni-Core\requirements.txt"

  if (-not (Test-Path -LiteralPath $nmrReq) -or -not (Test-Path -LiteralPath $uniReq)) {
    return
  }

  if (-not (Test-PythonModules $PythonExe @("torch"))) {
    Write-Host "[backend] Installing CPU PyTorch for NMR prediction runtime..."
    & $UvExe pip install --python $PythonExe --index-url https://download.pytorch.org/whl/cpu torch
    if ($LASTEXITCODE -ne 0) {
      exit $LASTEXITCODE
    }
  }

  if (-not (Test-PythonModules $PythonExe @("rdkit", "numpy", "matplotlib", "lmdb", "remotezip", "sklearn", "joblib", "iopath", "ml_collections", "scipy", "tensorboardX", "tokenizers", "wandb", "ase"))) {
    Write-Host "[backend] Installing NMR prediction skill dependencies..."
    & $UvExe pip install --python $PythonExe -r $nmrReq -r $uniReq ase
    if ($LASTEXITCODE -ne 0) {
      exit $LASTEXITCODE
    }
  }
}

if ($ScienceRoot) {
  $ScienceVenvDir = Join-Path $ScienceRoot ".venv"
  $ScienceScriptsDir = Join-Path $ScienceVenvDir "Scripts"
  $SciencePython = Join-Path $ScienceScriptsDir "python.exe"

  $ScienceBasePrefix = Get-PythonBasePrefix $SciencePython
  if ($ScienceBasePrefix -and ((Normalize-ExistingPath $ScienceBasePrefix) -ne (Normalize-ExistingPath $BackendBasePrefix))) {
    $resolvedScienceRoot = Normalize-ExistingPath $ScienceRoot
    $resolvedScienceVenv = Normalize-ExistingPath $ScienceVenvDir
    $expectedScienceVenv = Normalize-ExistingPath (Join-Path $ScienceRoot ".venv")

    if ($resolvedScienceVenv -ne $expectedScienceVenv -or -not $resolvedScienceVenv.StartsWith($resolvedScienceRoot)) {
      throw "Refusing to remove unexpected GVIM science virtualenv path: $ScienceVenvDir"
    }

    Write-Host "[backend] Recreating GVIM science .venv (current interpreter base is $ScienceBasePrefix, expected $BackendBasePrefix)..."
    Remove-Item -LiteralPath $ScienceVenvDir -Recurse -Force
  }

  if (-not (Test-Path $SciencePython)) {
    Write-Host "[backend] Syncing GVIM science command environment..."
    Push-Location $ScienceRoot
    try {
      if (Test-Path (Join-Path $ScienceRoot "uv.lock")) {
        & $UvExe sync --frozen --extra all --python $BackendBasePython
      } else {
        & $UvExe sync --extra all --python $BackendBasePython
      }
      if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
      }
    } finally {
      Pop-Location
    }
  }

  if (Test-Path $SciencePython) {
    $env:GVIM_SCIENCE_ROOT = $ScienceRoot
    $env:GVIM_SCIENCE_VENV = $ScienceVenvDir
    $env:GVIM_SCIENCE_PYTHON = $SciencePython
    $env:GVIM_SCIENCE_RUNTIME_ROOT = Join-Path $BackendDir "packages\harness"
    $env:DEER_FLOW_COMMAND_VENV = $ScienceVenvDir
    $env:DEER_FLOW_COMMAND_PYTHON = $SciencePython
    if (-not $env:GVIM_SCIENCE_ENV_FILE) {
      $env:GVIM_SCIENCE_ENV_FILE = Join-Path $ScienceRoot "config\materials-project.env"
    }
  }
}

$syncArgs = @("sync", "--frozen", "--all-packages", "--no-dev")
if ($env:DEER_FLOW_BACKEND_DEV_DEPS -eq "1") {
  $syncArgs = @("sync", "--frozen", "--all-packages")
}

if ($env:DEER_FLOW_BACKEND_EXTRAS) {
  $extras = $env:DEER_FLOW_BACKEND_EXTRAS -split "[,;\s]+" | Where-Object { $_ }
  foreach ($extra in $extras) {
    $syncArgs += @("--extra", $extra)
  }
}

Write-Host "[backend] Syncing Python dependencies into backend\.venv..."
& $UvExe @syncArgs --python $BackendBasePython
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

Ensure-NmrSkillRuntimeDeps $env:DEER_FLOW_COMMAND_PYTHON

& $env:DEER_FLOW_BACKEND_PYTHON -c "import sys; print(f'[backend] Python {sys.version.split()[0]} ({sys.executable})'); print(f'[backend] Python base {sys.base_prefix}')"
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

Write-Host "[backend] Starting Gateway API on 127.0.0.1:8001..."
& $env:DEER_FLOW_BACKEND_PYTHON -m uvicorn app.gateway.app:app --host 127.0.0.1 --port 8001
exit $LASTEXITCODE
