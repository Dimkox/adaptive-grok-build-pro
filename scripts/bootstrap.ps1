$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
py -3 scripts/grok_doctor.py
py -3 -m unittest discover -s tests -v
Write-Host "Ready. Start Grok Build here and trust project config/hooks."
