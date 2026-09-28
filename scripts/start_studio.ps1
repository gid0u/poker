$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot
$env:PYTHONPATH = Join-Path $repoRoot 'src'
$studioPython = Join-Path $repoRoot '.venv-studio\Scripts\python.exe'
if (Test-Path -LiteralPath $studioPython) {
    & $studioPython -m poker_evaluator.gui
} else {
    python -m poker_evaluator.gui
}
