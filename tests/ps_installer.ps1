# Checks install.ps1 / uninstall.ps1 (run from the project root):
#   powershell -ExecutionPolicy Bypass -File tests\ps_installer.ps1          (Windows PowerShell 5.1)
#   pwsh -File tests\ps_installer.ps1                                         (PowerShell 7)
# 1. both parse without errors and are ASCII;
# 2. install.ps1 dry run, run the way the one-liner runs it (text | iex). Changes nothing.

$root = Split-Path -Parent $PSScriptRoot
$fail = 0
Write-Host ("PowerShell {0}" -f $PSVersionTable.PSVersion)

foreach ($name in @("install.ps1", "uninstall.ps1")) {
    $path = Join-Path $root $name
    $tokens = $null
    $errors = $null
    [System.Management.Automation.Language.Parser]::ParseFile($path, [ref]$tokens, [ref]$errors) | Out-Null
    if ($errors.Count -eq 0) { Write-Host ("  ok    parses  {0}" -f $name) } else { Write-Host ("  FAIL  parses  {0}: {1}" -f $name, $errors[0]); $fail++ }
    $bytes = [System.IO.File]::ReadAllBytes($path)
    $bad = @($bytes | Where-Object { $_ -gt 127 }).Count
    if ($bad -eq 0) { Write-Host ("  ok    ASCII   {0}" -f $name) } else { Write-Host ("  FAIL  ASCII   {0}: {1} bytes" -f $name, $bad); $fail++ }
}

if ($args -contains "-NoDryRun") { exit $fail }

Write-Host ""
Write-Host "--- install.ps1 dry run (text | iex) ---"
$env:ICSPL_DRYRUN = "1"
try {
    Get-Content -Path (Join-Path $root "install.ps1") -Raw | Invoke-Expression
} catch {
    Write-Host ("  FAIL  dry run: {0}" -f $_.Exception.Message); $fail++
} finally {
    Remove-Item Env:\ICSPL_DRYRUN -ErrorAction SilentlyContinue
}
Write-Host ""
Write-Host ("{0} failure(s)" -f $fail)
exit $fail
