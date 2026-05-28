param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

if ($Clean) {
    if (Test-Path ".\build") { Remove-Item ".\build" -Recurse -Force }
    if (Test-Path ".\dist") { Remove-Item ".\dist" -Recurse -Force }
    if (Test-Path ".\nDisplayLauncherGenerator.spec") { Remove-Item ".\nDisplayLauncherGenerator.spec" -Force }
}

uv sync --group dev

uv run pyinstaller `
  --name nDisplayLauncherGenerator `
  --onefile `
  --windowed `
  --collect-all tkinter `
  src/ndisplay_launcher_generator/app.py

Write-Host ""
Write-Host "Build completed. EXE:"
Write-Host "  dist\nDisplayLauncherGenerator.exe"

