# ICSPL Export installer (pyRevit extension, Revit 2024-2026)
#
# Paste this in PowerShell (no admin needed):
#   irm https://raw.githubusercontent.com/akashnethaji990-a11y/ICSPL-Export/main/install.ps1 | iex
#
# What it does:
#   1. pyRevit missing -> installs the latest pyRevit.
#      pyRevit older than the latest release -> updates it to the latest.
#      pyRevit already the latest -> leaves it.
#   2. Installs ICSPL Export only (other pyRevit tools are not touched):
#      %APPDATA%\ICSPLExport\Extension\ICSPL Export.extension, and adds that folder to
#      pyRevit's extension list. Running it again updates ICSPL Export.
#      Saved settings (%APPDATA%\ICSPLExport\settings.json) are kept.
#
# Dry run (shows the steps, changes nothing):
#   $env:ICSPL_DRYRUN = "1"; irm https://raw.githubusercontent.com/akashnethaji990-a11y/ICSPL-Export/main/install.ps1 | iex
#
# Works in Windows PowerShell 5.1 and PowerShell 7. Keep this file ASCII.

function Install-ICSPLExport {
    $ErrorActionPreference = "Stop"
    $ProgressPreference = "SilentlyContinue"
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

    $Repo = "akashnethaji990-a11y/ICSPL-Export"
    $Branch = "main"
    $ExtName = "ICSPL Export.extension"
    $InstallTo = Join-Path (Join-Path $env:APPDATA "ICSPLExport") "Extension"
    $DryRun = ($env:ICSPL_DRYRUN -eq "1")
    $Headers = @{ "User-Agent" = "ICSPL-Export-Installer" }

    function Say($text, $color) {
        if (-not $color) { $color = "Gray" }
        Write-Host $text -ForegroundColor $color
    }
    function Step($text) { Write-Host ""; Write-Host ("== " + $text) -ForegroundColor Cyan }
    function Fail($text) { Write-Host ""; Write-Host ("STOPPED: " + $text) -ForegroundColor Red }

    function Find-PyRevit {
        $list = @()
        $cmd = Get-Command pyrevit -ErrorAction SilentlyContinue
        if ($cmd) { $list += $cmd.Source }
        $list += (Join-Path $env:APPDATA "pyRevit-Master\bin\pyrevit.exe")
        if ($env:ProgramFiles) { $list += (Join-Path $env:ProgramFiles "pyRevit-Master\bin\pyrevit.exe") }
        foreach ($p in $list) {
            if ($p -and (Test-Path $p)) { return $p }
        }
        return $null
    }

    function Get-PyRevitVersion($exe) {
        $text = (& $exe --version 2>&1 | Out-String)
        if ($text -match "v(\d+\.\d+\.\d+(\.\d+)?)") { return [version]$Matches[1] }
        return $null
    }

    function Get-RegisteredPaths($exe) {
        $out = @()
        foreach ($line in (& $exe extensions paths 2>&1)) {
            $t = ("" + $line).Trim()
            if ($t -and -not $t.StartsWith("==>") -and (Test-Path $t)) { $out += $t }
        }
        return $out
    }

    function Test-SamePath($a, $b) {
        return ($a.TrimEnd("\") -ieq $b.TrimEnd("\"))
    }

    Say "ICSPL Export installer" "White"
    if ($DryRun) { Say "DRY RUN: nothing is downloaded to install or changed." "Yellow" }

    # ------------------------------------------------------------ 1. pyRevit
    Step "1. pyRevit"
    $exe = Find-PyRevit
    $current = $null
    if ($exe) {
        $current = Get-PyRevitVersion $exe
        Say ("Installed: pyRevit {0}  ({1})" -f $current, $exe)
    } else {
        Say "Installed: none"
    }

    $release = $null
    try {
        $release = Invoke-RestMethod -Uri "https://api.github.com/repos/pyrevitlabs/pyRevit/releases/latest" -Headers $Headers
    } catch {
        Say ("Could not read the latest pyRevit release from GitHub: {0}" -f $_.Exception.Message) "Yellow"
    }
    $latest = $null
    if ($release -and ($release.tag_name -match "(\d+\.\d+\.\d+(\.\d+)?)")) { $latest = [version]$Matches[1] }
    if ($latest) { Say ("Latest:    pyRevit {0}" -f $latest) }

    $admin = $false
    if ($exe -and $env:ProgramFiles -and $exe.StartsWith($env:ProgramFiles, [StringComparison]::OrdinalIgnoreCase)) { $admin = $true }

    $need = ""
    if (-not $exe) { $need = "install" }
    elseif ($latest -and $current -and ($current -lt $latest)) { $need = "update" }

    if ($need -and -not $release) {
        if (-not $exe) { Fail "pyRevit is not installed and the latest release could not be read. Check the internet connection and run again."; return }
        Say "pyRevit is not updated (latest release unknown)." "Yellow"
        $need = ""
    }

    if (-not $need) {
        Say "pyRevit is up to date: nothing to do." "Green"
    } else {
        if ($admin) { $pattern = "^pyRevit_[\d\.]+_admin_signed\.exe$" } else { $pattern = "^pyRevit_[\d\.]+_signed\.exe$" }
        $asset = $release.assets | Where-Object { $_.name -match $pattern } | Select-Object -First 1
        if (-not $asset) { Fail ("No pyRevit installer found in release {0}." -f $release.tag_name); return }
        $what = "Install"
        if ($need -eq "update") { $what = "Update" }
        Say ("{0} pyRevit {1} with {2}{3}" -f $what, $latest, $asset.name, $(if ($admin) { " (all users: Windows asks for admin rights)" } else { "" }))

        if ($DryRun) {
            if (Get-Process -Name Revit -ErrorAction SilentlyContinue) { Say "Revit is open: you would be asked to close it first." "Yellow" }
            Say "DRY RUN: pyRevit not changed." "Yellow"
        } else {
            while (Get-Process -Name Revit -ErrorAction SilentlyContinue) {
                Say "Revit is open. Close Revit (save your work first)." "Yellow"
                $answer = Read-Host "Press Enter when Revit is closed, or type S to skip the pyRevit step"
                if ($answer -match "^[sS]") { break }
            }
            if (Get-Process -Name Revit -ErrorAction SilentlyContinue) {
                if (-not $exe) { Fail "pyRevit is needed. Close Revit and run the installer again."; return }
                Say "pyRevit step skipped; ICSPL Export is installed with the current pyRevit." "Yellow"
            } else {
                $file = Join-Path $env:TEMP $asset.name
                Say ("Downloading {0} ({1:N0} MB) ..." -f $asset.name, ($asset.size / 1MB))
                Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $file -UseBasicParsing -Headers $Headers
                Say "Running the pyRevit installer (a few minutes) ..."
                $args_ = @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-")
                if ($admin) {
                    $proc = Start-Process -FilePath $file -ArgumentList $args_ -Verb RunAs -Wait -PassThru
                } else {
                    $proc = Start-Process -FilePath $file -ArgumentList $args_ -Wait -PassThru
                }
                Remove-Item $file -Force -ErrorAction SilentlyContinue
                if ($proc.ExitCode -ne 0) { Fail ("The pyRevit installer ended with code {0}." -f $proc.ExitCode); return }
                $exe = Find-PyRevit
                if (-not $exe) { Fail "pyRevit was installed but pyrevit.exe was not found. Restart the PC and run again."; return }
                Say ("Attaching pyRevit to the installed Revit versions ...")
                & $exe attach master default --installed 2>&1 | Out-Null
                Say ("pyRevit {0} ready." -f (Get-PyRevitVersion $exe)) "Green"
            }
        }
    }

    if (-not $exe) {
        if ($DryRun) { Say "DRY RUN: the ICSPL Export step needs pyRevit; it would run after pyRevit is installed." "Yellow"; return }
        Fail "pyRevit not found."
        return
    }

    # ------------------------------------------------------------ 2. ICSPL Export
    Step "2. ICSPL Export"
    $registered = Get-RegisteredPaths $exe
    foreach ($p in $registered) {
        if (-not (Test-SamePath $p $InstallTo) -and (Test-Path (Join-Path $p $ExtName))) {
            Say ("ICSPL Export is already loaded from another folder: {0}" -f $p) "Yellow"
            Say "Not installed a second time, so Revit does not show two Export tabs." "Yellow"
            Say "(To use the installed copy instead, remove that folder from pyRevit > Settings > Custom Extension Directories.)"
            if (-not $DryRun) { return }
            Say "DRY RUN: checking the download anyway." "Yellow"
        }
    }

    $tmp = Join-Path $env:TEMP ("icspl_export_" + [guid]::NewGuid().ToString("N").Substring(0, 8))
    New-Item -ItemType Directory -Path $tmp | Out-Null
    try {
        $zip = Join-Path $tmp "tool.zip"
        Say ("Downloading ICSPL Export from github.com/{0} ..." -f $Repo)
        Invoke-WebRequest -Uri ("https://github.com/{0}/archive/refs/heads/{1}.zip" -f $Repo, $Branch) -OutFile $zip -UseBasicParsing -Headers $Headers
        Expand-Archive -Path $zip -DestinationPath $tmp -Force
        $src = Get-ChildItem -Path $tmp -Recurse -Directory -Filter $ExtName | Select-Object -First 1
        if (-not $src) { Fail ("{0} not found in the download." -f $ExtName); return }

        $version = ""
        try {
            $commit = Invoke-RestMethod -Uri ("https://api.github.com/repos/{0}/commits/{1}" -f $Repo, $Branch) -Headers $Headers
            $version = "{0} ({1})" -f $commit.sha.Substring(0, 7), $commit.commit.committer.date
        } catch { $version = "unknown" }
        Say ("Version: {0}" -f $version)

        $dest = Join-Path $InstallTo $ExtName
        $isRegistered = $false
        foreach ($p in $registered) { if (Test-SamePath $p $InstallTo) { $isRegistered = $true } }
        $verb = "Install to"
        if (Test-Path $dest) { $verb = "Update" }

        if ($DryRun) {
            Say ("DRY RUN: would {0} {1}" -f $verb.ToLower(), $dest) "Yellow"
            if (-not $isRegistered) { Say ("DRY RUN: would add {0} to pyRevit's extension list" -f $InstallTo) "Yellow" }
            return
        }

        Say ("{0} {1}" -f $verb, $dest)
        if (Test-Path $dest) { Remove-Item -Path $dest -Recurse -Force }
        New-Item -ItemType Directory -Path $InstallTo -Force | Out-Null
        Copy-Item -Path $src.FullName -Destination $dest -Recurse -Force
        Set-Content -Path (Join-Path $InstallTo "version.txt") -Value ("ICSPL Export {0}, installed {1}" -f $version, (Get-Date -Format "yyyy-MM-dd HH:mm")) -Encoding ASCII
        Get-ChildItem -Path $InstallTo -Recurse -File | Unblock-File

        if (-not $isRegistered) {
            & $exe extensions paths add $InstallTo 2>&1 | Out-Null
            $check = Get-RegisteredPaths $exe
            $ok = $false
            foreach ($p in $check) { if (Test-SamePath $p $InstallTo) { $ok = $true } }
            if (-not $ok) { Fail ("Could not add {0} to pyRevit. Add it by hand: pyRevit > Settings > Custom Extension Directories." -f $InstallTo); return }
            Say "Added to pyRevit's extension list."
        }
    } finally {
        Remove-Item -Path $tmp -Recurse -Force -ErrorAction SilentlyContinue
    }

    Write-Host ""
    Say "DONE. ICSPL Export is installed." "Green"
    if (Get-Process -Name Revit -ErrorAction SilentlyContinue) {
        Say "Revit is open: click pyRevit tab > Reload (or restart Revit). The Export tab appears."
    } else {
        Say "Start Revit: the Export tab appears."
    }
}

Install-ICSPLExport
