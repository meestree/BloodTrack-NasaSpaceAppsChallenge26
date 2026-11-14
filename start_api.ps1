# Start the development API from any working directory.
# Usage: .\start_api.ps1 --reload
# Override the interpreter: .\start_api.ps1 -PythonExecutable 'C:\path\python.exe'
param(
    [string]$PythonExecutable = ''
)

$ErrorActionPreference = 'Stop'
$projectDirectory = $PSScriptRoot

if (-not $PythonExecutable) {
    $candidates = @(
        (Join-Path $projectDirectory '.venv\Scripts\python.exe')
    )
    # Support this project's existing PyCharm Conda environment as well as venv.
    if ($env:USERPROFILE) {
        $candidates += Join-Path $env:USERPROFILE 'anaconda3\envs\NasaSpaceAppsChallenge26\python.exe'
        $candidates += Join-Path $env:USERPROFILE 'miniconda3\envs\NasaSpaceAppsChallenge26\python.exe'
    }
    if ($env:CONDA_PREFIX) {
        $candidates += Join-Path $env:CONDA_PREFIX 'python.exe'
    }
    $PythonExecutable = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
}

if (-not $PythonExecutable -or -not (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)) {
    Write-Host 'No project Python interpreter found.' -ForegroundColor Red
    Write-Host 'Use -PythonExecutable with the full path to your project python.exe, or create .venv:'
    Write-Host '  py -3 -m venv .venv'
    Write-Host '  .\.venv\Scripts\python.exe -m pip install -e .'
    exit 1
}

$PythonExecutable = (Resolve-Path -LiteralPath $PythonExecutable).Path
Push-Location -LiteralPath $projectDirectory
try {
    if (-not (Test-Path -LiteralPath (Join-Path $projectDirectory 'data\astronautas.db') -PathType Leaf)) {
        Write-Host 'The database is missing: data\astronautas.db' -ForegroundColor Red
        Write-Host 'Restore the supplied database to that location, then run this launcher again.'
        exit 1
    }
    & $PythonExecutable -c "import importlib.util, sys; sys.exit(0 if sys.version_info >= (3, 11) and all(importlib.util.find_spec(name) is not None for name in ('fastapi', 'uvicorn', 'pydantic', 'pwdlib', 'argon2', 'email_validator')) else 1)"
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'The API requires Python 3.11 or newer and its backend dependencies.' -ForegroundColor Red
        Write-Host ('Install dependencies: & "{0}" -m pip install -e .' -f $PythonExecutable)
        exit 1
    }
    Write-Host 'Starting API. Default address: http://127.0.0.1:8000'
    Write-Host 'Default API documentation: http://127.0.0.1:8000/docs'
    Write-Host 'Additional options can override the address; see the Uvicorn startup message below.'
    Write-Host 'Press Ctrl+C to stop.'
    & $PythonExecutable -m uvicorn backend.main:app `
        --app-dir (Join-Path $projectDirectory 'src') `
        --host 127.0.0.1 `
        --port 8000 `
        @args
    $apiExitCode = $LASTEXITCODE
    if ($apiExitCode -ne 0) {
        Write-Host 'If dependencies are missing, install them in the selected environment:' -ForegroundColor Yellow
        Write-Host ('  & "{0}" -m pip install -e .' -f $PythonExecutable)
    }
}
finally {
    Pop-Location
}
exit $apiExitCode
