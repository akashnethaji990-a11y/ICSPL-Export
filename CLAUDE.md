# CLAUDE.md - ICSPL Export

## Keep separate
- This is its own project. Do not open, read, copy from, import from or reference any
  other pyRevit project. In particular, do not touch the SBP project under
  `OneDrive - IC Singapore\COMPANY SET UP\pyRevit\` (SBP.extension). No shared code.

## Target
- Revit 2024-2026 (one code base), pyRevit 5.2, IronPython 2.7.
- IronPython rules: no f-strings (use "{0}".format()), no type hints, no pathlib,
  keep source ASCII, use os.path.
- Scripts get `__revit__` injected by pyRevit. `ICSPL Export.extension/lib` is on the
  import path, so buttons do `import icspl_export`.
- bundle.yaml `layout:` lines are folder names WITHOUT the extension ("PDF Print", not
  "PDF Print.pushbutton"). pyRevit drops anything not matched, and an empty panel/tab
  is not drawn at all.

## Steps
- Step 1 (done 19 Oct, tab confirmed in Revit 2026): Export tab, placeholder buttons.
- Step 2: export code. Ask the questions one tool at a time, PDF first, then DWG, then
  NWC, then IFC. Do not write export code before the answers are in.
  - PDF: answers in, built 19 Oct (HISTORY 0.2.0), waiting for Akash's Revit test.
  - DWG: answers in (23 Nov), built 23 Nov (HISTORY 0.3.0), waiting for the Revit test.
  - NWC: answers in (23 Nov), built 23 Nov (HISTORY 0.4.0), waiting for the Revit test.
  - IFC: answers in (23 Nov), built 23 Nov (HISTORY 0.5.0), waiting for the Revit test.
  - All four formats are built. Next: Akash's Revit tests of each.

## Decisions (Akash, 19 Oct)
- One Export window for all formats (lib/icspl_window.py + lib/ExportWindow.xaml). Each
  button opens it with its own format ticked; more formats can be ticked; one click =
  one run.
- Every run makes a NEW folder in the picked main folder: YYMMDD_<initials>- (e.g.
  261019_ANE-, trailing dash on purpose), then (2), (3) ... if it exists. Inside it:
  PDF\ and CAD\ (DWG); the NWC and IFC files go straight in it (no subfolder).
  Main folder = Browse, remembered. Initials in the window, remembered (default ANE).
- Sheets: three sources in the window: Pick from list (search, tick all/none,
  pre-ticked from the Browser selection), Selected in Browser, Revit Sheet Set.
  Only Pick lets you change ticks. Placeholder sheets are left out.
- File name (PDF and later CAD; Akash, 23 Nov) = drawing number with "/" -> "-", then
  "-" + Current Revision (built-in SHEET_CURRENT_REVISION). Revision "-" or empty -> one
  "-" at the end. Example: PRJ01/ICSPL/Z01/ZZ/S/STR/DR/DET/3791 rev 0.6 ->
  PRJ01-ICSPL-Z01-ZZ-S-STR-DR-DET-3791-0.6. Code: X.drawing_file_name.
  - No parameter holds the full drawing number. It is built like the title block
    (R.PROJECT_PARTS + R.SHEET_PARTS): Project Info "Project Number" / "Organization
    Name" / sheet "Project Location Code" / "Zone/Level" / "Role" / "Discipline" /
    "Type Code" / "Sub-Type" / Sheet Number. Akash confirmed (each authority differs).
  - "Revision No" on sheets is "-" almost everywhere: NOT used.
  - An empty part stays empty ("--"), not edited (Akash): sheets 3000/3001 have no
    Project Location Code -> PRJ01-ICSPL--ZZ-S-STR-DR-CVS-3000-.
  - Checked in the live model with the real code: 141 sheets, 141 unique names.
  - Other bad characters \ : * ? " < > | -> "-", listed in the report. Empty name ->
    skip + report. Same file name twice -> " (2)".
- PDF setup (23 Nov): picked in the window from the model's PDF export setups (last
  used, else active). Its options are used as saved + the 4 hide options always ON
  (Akash, option B), except Combine/FileName (our
  names). No setups -> the 19 Oct settings below ("<ICSPL default>").
- PDF: one file per sheet (name above) plus one combined file <model>_<YYMMDD>.pdf
  (model = central model name). Same options object for both, and the combined file
  holds exactly the sheets whose single PDF was written.
  - Colour, sheet size (ExportPaperFormat.Default), vector, raster High, zoom 100 %,
    centred. Hidden: reference/work planes, scope boxes, crop boundaries,
    unreferenced view tags (covers unreferenced section marks).
  - Each sheet is its own doc.Export(Combine=True, FileName=number) call, so the name
    is exact and one failure does not stop the rest.

- DWG (Akash, 23 Nov): CAD\ folder, one DWG per sheet, same file names as the PDFs,
  views merged into the sheet (MergedViews, no xrefs), AutoCAD 2018 (ACADVersion.R2018
  = Default = 28). Layers/colours from a DWG export setup of the model picked in the
  window (last used, else the model's active one; "<Revit default>" if none). Same
  sheet list as PDF. No combined DWG. doc.Export(folder, name, [sheet], options).

- NWC (Akash, 23 Nov): one file <model name>.nwc in the dated folder root, from a 3D
  view picked in the window ("NWC 3D view": last used, else the view named like the
  model, else the first). Only what the view shows (ExportScope View). Shared
  coordinates, all parameters, not divided by levels, no rooms.
  - "Only STR model elements, nothing linked": ExportLinks False,
    ConvertLinkedCADFormats False, and every Revit/IFC link, CAD link/import, point
    cloud and PDF/image visible in the view is hidden in a transaction that is rolled
    back after the export (model not changed). Fallback if Revit refuses to export
    inside it: hide, export, show again. The report lists what was left out.
  - Exporter missing for the running Revit -> NWC tick box off with the reason.

- IFC (Akash, 23 Nov): one file <model name>.ifc in the dated folder root, ALWAYS the
  setup "IFC-SG Regulatory Requirements View" (X.IFC_SETUP, no dropdown), from the SAME
  3D view as NWC (one "3D view" dropdown for both; label "NWC/IFC 3D view").
  - The setups are read by Revit's own IFC exporter add-in (IFCExporterUIOverride.dll,
    BIM.IFC.Export.UI): IFCExportConfigurationsMap AddBuiltInConfigurations +
    AddSavedConfigurations, then config.UpdateOptions(options, viewId). Both need
    IFCCommandOverrideApplication.TheDocument = doc (set, then restored).
  - IFC-SG is a BUILT-IN setup; the model (P200 PIM-0004) saves changes to it in
    DataStorage schema IFCExportConfigurationMap (GUID c2a3e6fe-..., field MapField =
    JSON string). The map merges them. Model also has "IFC Configuration - To Consultant"
    (IFC2x3 CV2.0), not used.
  - Its mapping file points to C:\Program Files\Autodesk\Revit 2024\AddIns\
    IFCExporterUI\IFC-SG Property Mapping Export.txt (missing). Akash: use the same
    file from the running Revit's IFC add-in folder (X.replacement_file), on a Clone()
    only; the setup in the model is not changed. Report shows it.
  - Nothing linked (same rule as NWC): ExportLinkedFiles forced DontExport, linked
    items hidden in the IFC transaction, which is rolled back (no IFC GUIDs stored).
  - Exporter or setup missing -> IFC tick box off with the reason.

## Tests (offline)
- `python tests\test_icspl_export.py` (pure helpers, 20).
- The Bash tool unescapes backslashes in inline heredoc scripts ("\\n" became a real
  newline, "tests\\test" a tab). For edits with backslashes use the Edit tool or a
  script file. A crashed inline edit once emptied tests\test_icspl_export.py.
- In pyRevit's IronPython 2.7 engine (netfx, as Revit 2024):
  `powershell -ExecutionPolicy Bypass -File tools\ipy_run.ps1 -Py <test>` for
  tests\test_icspl_export.py, tests\ipy_window.py (window, 35 checks, opens off-screen
  for a moment), tests\ipy_syntax.py (compile + ASCII + Revit API names).
- tools\ipy_run.ps1 is this project's own host. It finds pyRevit in
  %APPDATA%\pyRevit-Master (pyRevit 7, since Nov) or C:\Program Files\pyRevit-Master (5.x).
  The netcore engine can't import os
  under pwsh 7.6 / .NET 10, so it defaults to netfx.

## Export rules (for Step 2)
- PDF: Revit PDFExportOptions + doc.Export(folder, viewIds, options).
- DWG: DWGExportOptions, or a named ExportDWGSettings from the model.
- NWC: NavisworksExportOptions. Needs the free Autodesk "Navisworks NWC Export Utility"
  for Revit 2026. Check OptionalFunctionalityUtils.IsNavisworksExporterAvailable() and
  show a clear message if it is missing.
- IFC: IFCExportOptions + doc.Export(folder, name, options). Revit requires an open
  Transaction for IFC export (roll it back afterwards). Ask in Step 2 which IFC version
  and which setup (named setups belong to the IFC exporter add-in, not the plain API).
- Every export ends with a report: files written, sizes, skipped items with reasons.
- Settings are remembered in %APPDATA%\ICSPLExport\settings.json.

## Repo
- Own git repo, branch main. Remote origin = GitHub akashnethaji990-a11y/ICSPL-Export,
  which is PUBLIC (shared with colleagues). Do not commit or push unless asked.
- PUBLIC repo rule (Akash, 23 Nov): only the ICSPL name may appear. No client or
  project names in any tracked file (code, tests, docs, commit messages). Use made-up
  examples: PRJ01/ICSPL/Z01/... drawing numbers, model P200-ICSPL-BLK1-..., "To
  Consultant", "Authority". Scan before every push (scratchpad clean_names.py list).
  Results of live checks: describe them without the real model/project names.
- Local branch backup-with-client-names holds the first Step 2 commit with the real
  names: NEVER push it.

## Install for colleagues (Akash, 23 Nov: one terminal line, like his ERSS tool)
- `irm https://raw.githubusercontent.com/akashnethaji990-a11y/ICSPL-Export/main/install.ps1 | iex`
  (install.ps1 at the repo root; needs the public repo + push to main to work).
  - pyRevit: none -> latest; older than the latest GitHub release -> update; else
    leave. Per-user installer pyRevit_<v>_signed.exe (admin one if pyRevit is in
    Program Files), Inno flags /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-, then
    `pyrevit attach master default --installed`. Revit must be closed (asks; S skips).
  - Tool: GitHub ZIP of main -> %APPDATA%\ICSPLExport\Extension\ICSPL Export.extension
    (replaced on update; settings.json beside it kept), Unblock-File, then
    `pyrevit extensions paths add %APPDATA%\ICSPLExport\Extension`.
  - If another registered pyRevit path already holds ICSPL Export.extension (Akash's
    development folder), it stops: no second Export tab.
  - Dry run: $env:ICSPL_DRYRUN = "1". uninstall.ps1 = paths forget + delete the folder.
  - ERSS has its own installer and stays separate; nothing here reads or calls it.
- Test: `powershell -ExecutionPolicy Bypass -File tests\ps_installer.ps1` (parse +
  ASCII in 5.1, dry run as text | iex). `pwsh -File tests\ps_installer.ps1 -NoDryRun`.
- Log each change in HISTORY.md.

## Version rules
- Read the version with `revit_year(__revit__.Application)`. Do not hard-code 2026.
- Use `element_id_value()` from lib/icspl_export.py instead of `.IntegerValue` or `.Value` directly.
- Any API that differs between 2024 and 2026 goes behind a helper in lib/icspl_export.py.
- The NWC utility is installed per Revit year. Check it for the running version.
