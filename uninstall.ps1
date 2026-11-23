# ICSPL Export uninstaller
#
# Paste this in PowerShell:
#   irm https://raw.githubusercontent.com/akashnethaji990-a11y/ICSPL-Export/main/uninstall.ps1 | iex
#
# Removes only what install.ps1 added: the folder %APPDATA%\ICSPLExport\Extension and
# its entry in pyRevit's extension list. pyRevit and other tools are not touched.
# Saved settings (%APPDATA%\ICSPLExport\settings.json) are kept.
# Keep this file ASCII.

function Uninstall-ICSPLExport {
    $ErrorActionPreference = "Stop"
    $InstallTo = Join-Path (Join-Path $env:APPDATA "ICSPLExport") "Extension"

    $exe = $null
    $list = @()
    $cmd = Get-Command pyrevit -ErrorAction SilentlyContinue
    if ($cmd) { $list += $cmd.Source }
    $list += (Join-Path $env:APPDATA "pyRevit-Master\bin\pyrevit.exe")
    if ($env:ProgramFiles) { $list += (Join-Path $env:ProgramFiles "pyRevit-Master\bin\pyrevit.exe") }
    foreach ($p in $list) { if (-not $exe -and $p -and (Test-Path $p)) { $exe = $p } }

    Write-Host "ICSPL Export uninstaller" -ForegroundColor White
    if ($exe) {
        & $exe extensions paths forget $InstallTo 2>&1 | Out-Null
        Write-Host ("Removed from pyRevit's extension list: {0}" -f $InstallTo)
    } else {
        Write-Host "pyRevit not found: nothing to remove from its list." -ForegroundColor Yellow
    }
    if (Test-Path $InstallTo) {
        Remove-Item -Path $InstallTo -Recurse -Force
        Write-Host ("Deleted: {0}" -f $InstallTo)
    } else {
        Write-Host "ICSPL Export folder not found (already removed)."
    }
    Write-Host ""
    Write-Host "DONE. Restart Revit (or pyRevit tab > Reload): the Export tab is gone." -ForegroundColor Green
    Write-Host "Your settings are kept in %APPDATA%\ICSPLExport\settings.json."
}

Uninstall-ICSPLExport
