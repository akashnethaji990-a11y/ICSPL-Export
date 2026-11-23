# Run a Python file in pyRevit's own IronPython 2.7.12 engine, outside Revit.
# No Revit API here: use it for syntax checks, pure helpers and the WPF window.
#
#   powershell -ExecutionPolicy Bypass -File tools\ipy_run.ps1 -Py tests\ipy_window.py
#
# Default = the netfx engine (the one Revit 2024 uses), run from Windows PowerShell 5.1.
# The netcore engine (Revit 2025-2026, .NET 8) cannot "import os" when pwsh runs it on
# .NET 10, so -Fx netcore only helps for code that needs no stdlib.
# Exit code 0 = the script ran without an exception.
param(
    [Parameter(Mandatory = $true)][string]$Py,
    [ValidateSet("netcore", "netfx")][string]$Fx = "netfx",
    [string]$PyRevit = ""
)
$ErrorActionPreference = "Stop"
if (-not $PyRevit) {
    # pyRevit 7 installs per user; 5.x installed in Program Files
    $PyRevit = @((Join-Path $env:APPDATA "pyRevit-Master"), "C:\Program Files\pyRevit-Master") |
        Where-Object { Test-Path (Join-Path $_ "bin") } | Select-Object -First 1
    if (-not $PyRevit) { Write-Error "pyRevit install not found; pass -PyRevit <folder>" }
}
$root = Split-Path -Parent $PSScriptRoot
$eng = Join-Path $PyRevit "bin\$Fx\engines\IPY2712PR"
if (-not (Test-Path $eng)) { Write-Error "pyRevit engine not found: $eng" }

Add-Type -AssemblyName PresentationFramework, PresentationCore, WindowsBase, System.Xaml, System.Windows.Forms
$names = "pyRevitLabs.Microsoft.Scripting", "pyRevitLabs.Microsoft.Dynamic", "pyRevitLabs.IronPython",
         "pyRevitLabs.IronPython.Modules", "pyRevitLabs.IronPython.Wpf"
$asm = @{}
foreach ($n in $names) { $asm[$n] = [Reflection.Assembly]::LoadFrom((Join-Path $eng "$n.dll")) }

# The IronPython 2.7 standard library (os, json ...) is a zip inside pyRevitLoader.dll.
# Unpacked to a folder once (importing from the zip fails on .NET 10).
$stdlib = Join-Path $env:TEMP "ICSPLExport_ipy2712_$Fx"
if (-not (Test-Path (Join-Path $stdlib "os.py"))) {
    Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
    $loader = [Reflection.Assembly]::LoadFrom((Join-Path $eng "pyRevitLoader.dll"))
    $res = $loader.GetManifestResourceNames() | Where-Object { $_ -like "*python_2712pr_lib.zip" } | Select-Object -First 1
    if (-not $res) { Write-Error "IronPython stdlib not found in pyRevitLoader.dll" }
    $zip = New-Object IO.Compression.ZipArchive($loader.GetManifestResourceStream($res))
    [IO.Compression.ZipFileExtensions]::ExtractToDirectory($zip, $stdlib)
    $zip.Dispose()
}

$engine = [IronPython.Hosting.Python]::CreateEngine()
$paths = $engine.GetSearchPaths()
$paths.Add($stdlib)
$paths.Add((Join-Path $root "ICSPL Export.extension\lib"))
$paths.Add((Join-Path $root "tests"))
$paths.Add((Join-Path $PyRevit "pyrevitlib"))
$paths.Add((Join-Path $PyRevit "site-packages"))
$engine.SetSearchPaths($paths)

$scope = $engine.CreateScope()
$scope.SetVariable("_path", (Resolve-Path $Py).Path)
# same as pyrevit.framework: the wpf module lives in <prefix>IronPython.Wpf.dll
$scope.SetVariable("_wpf_dll", (Join-Path $eng "pyRevitLabs.IronPython.Wpf.dll"))
$boot = @"
import clr, sys, traceback
clr.AddReferenceToFileAndPath(_wpf_dll)
_code = 0
try:
    execfile(_path, {"__name__": "__main__", "__file__": _path})
except SystemExit as _e:
    _code = _e.code or 0
except Exception:
    traceback.print_exc()
    _code = 1
"@
try {
    $engine.Execute($boot, $scope) | Out-Null
} catch {
    Write-Host ("IronPython error: " + $_.Exception.Message)
    exit 1
}
exit [int]$scope.GetVariable("_code")
