# ICSPL Export (pyRevit extension)

Revit 2024-2026 - pyRevit 5.2 - IronPython 2.7

Export tools for ICSPL: **PDF Print**, **DWG Export**, **NWC Export**, **IFC Export**.

**Status: Step 2.** All four exports are built. PDF, DWG and NWC are being tested in
Revit; IFC is not yet tested.

## How an export works

1. Click a button: the Export window opens with that format ticked.
2. Pick the main folder (remembered) and your initials (remembered).
3. PDF / DWG: choose the sheets (Pick from list, Selected in Browser, or a Revit
   Sheet Set). NWC / IFC: choose the 3D view (one view for both).
4. Export. Every run makes a new folder:

       <main folder>\261019_ANE-\        (YYMMDD_initials-, then (2), (3) ...)
           PDF\   <drawing no>-<rev>.pdf per sheet + <model>_261019.pdf (combined)
           CAD\   <drawing no>-<rev>.dwg per sheet
           <model>.nwc                    shared coordinates, nothing linked
           <model>.ifc                    setup IFC-SG Regulatory Requirements View

5. A report lists the files written with sizes, and anything skipped with the reason.

## Install (one line)

Open **PowerShell** (Start menu > type `PowerShell` > Enter), paste this line and press Enter:

    irm https://raw.githubusercontent.com/akashnethaji990-a11y/ICSPL-Export/main/install.ps1 | iex

It does everything:

| Your PC has | The installer |
|---|---|
| No pyRevit | installs the latest pyRevit |
| An older pyRevit | updates it to the latest |
| The latest pyRevit | leaves it |
| Then, always | installs ICSPL Export only (other pyRevit tools are not touched) |

- No admin rights needed. If Revit is open and pyRevit must be updated, it asks you to
  close Revit first.
- Then start Revit: an **Export** tab appears with four buttons: PDF Print, DWG Export,
  NWC Export, IFC Export.
- **Update ICSPL Export:** paste the same line again.
- **Uninstall:** `irm https://raw.githubusercontent.com/akashnethaji990-a11y/ICSPL-Export/main/uninstall.ps1 | iex`
  (removes ICSPL Export only; pyRevit stays).
- Installed in `%APPDATA%\ICSPLExport\Extension`; your settings stay in
  `%APPDATA%\ICSPLExport\settings.json`.

## Load a developer copy in pyRevit (instead of the installer)

1. pyRevit tab > Settings > Custom Extension Directories > Add this folder
   (the folder that contains `ICSPL Export.extension`).
2. Save Settings and Reload. (The installer skips a PC that already loads a copy this
   way, so the Export tab never shows twice.)

## Icons

After changing icons, regenerate them from the project root:

    python tools\make_icons.py

This needs CPython 3 only (standard library, no installs).

## Layout

    ICSPL Export.extension/
      Export.tab/Export.panel/   the four pushbuttons (script.py + icons)
      lib/icspl_export.py        pure helpers (no Revit API, testable anywhere)
      lib/icspl_revit.py         Revit API: sheets, sheet sets, PDF export
      lib/icspl_window.py        Export window logic (+ lib/ExportWindow.xaml)
      lib/icspl_run.py           one run: window, folder, exports, report
    install.ps1 / uninstall.ps1  one-line installer (pyRevit + this tool) / uninstaller
    tools/make_icons.py          icon generator
    tools/ipy_run.ps1            run a test in pyRevit's IronPython 2.7 engine
    tests/                       offline tests (see CLAUDE.md "Tests")
    CLAUDE.md                    project notes for Claude sessions
    HISTORY.md                   change log

## Revit versions

Built for Revit 2024, 2025 and 2026 with one code base. The NWC export needs the
Autodesk "Navisworks NWC Export Utility" installed for each Revit year you use.
