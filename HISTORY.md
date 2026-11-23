# HISTORY

## 0.1.0 - 2026-10-13 - Step 1 scaffold
- Export tab with one panel and three placeholder buttons: PDF Print, DWG Export, NWC Export.
- lib/icspl_export.py: Revit version label, "coming soon" message, settings folder path.
- tools/make_icons.py: light and dark 96x96 icons, standard library only.
- README.md, CLAUDE.md, .gitignore.
- Export logic: not started (Step 2 waits for answers).

## 0.1.1 - 2026-10-19 - Target Revit 2024-2026
- Supported years set to 2024, 2025, 2026 (SUPPORTED_REVIT_YEARS in lib/icspl_export.py).
- lib: revit_year(), is_supported_revit(), element_id_value() (ElementId.Value / IntegerValue).
- Placeholder message warns when run in an unsupported Revit version.
- README.md and CLAUDE.md updated for the version range.

## 0.1.2 - 2026-10-19 - Fix: Export tab not showing
- Cause 1: the project folder was not in pyRevit's Custom Extension Directories. Added
  with `pyrevit extensions paths add` (pyRevit settings, not in this repo).
- Cause 2: Export.panel/bundle.yaml listed "PDF Print.pushbutton" etc. pyRevit matches
  layout lines against the folder name without its extension ("PDF Print"), and leaves
  out anything not matched, so the panel was empty and the tab was not drawn.
  Layout lines are now plain names.
- Confirmed in Revit 2026: Export tab shows PDF Print, DWG Export, NWC Export.

## 0.1.3 - 2026-10-19 - IFC Export placeholder
- Fourth button "IFC Export" (placeholder message, like the others), last in the panel.
- Icon: green, three stacked floor slabs (tools/make_icons.py, glyph "ifc").
  The other icons regenerate unchanged.
- make_icons.py docstring made raw (removed a SyntaxWarning).
- CLAUDE.md: IFC added to the Step 2 order and export rules. README: four buttons.

## 0.2.0 - 2026-10-19 - Step 2: PDF Print (not yet run in Revit)
- Step 1 done (Export tab confirmed in Revit 2026).
- PDF questions answered (decisions in CLAUDE.md "Decisions").
- lib/ExportWindow.xaml + lib/icspl_window.py: one Export window for all formats
  (PDF can be ticked; DWG/NWC/IFC "not built yet"), main folder + initials + preview of
  the new folder, three sheet sources, search, the reason when Export is off.
- lib/icspl_revit.py: sheets, Browser selection, sheet sets, central model name, PDF
  options, one-PDF export with rename fallback.
- lib/icspl_run.py: window -> new YYMMDD_<initials>- folder -> PDF\ singles + combined
  -> report in the pyRevit output (written + sizes, skipped + reason, renamed, options
  Revit refused). Progress bar with Cancel.
- lib/icspl_export.py: pure helpers (names, folder, plan, settings merge, report text).
- PDF Print button now runs the export. DWG/NWC/IFC buttons unchanged.
- tools/ipy_run.ps1 + tests (13 helper tests in CPython and IronPython, 35 window
  checks, compile/ASCII/API-name check). All pass.

### Revit test list for PDF Print
1. pyRevit Reload. PDF Print opens the Export window; PDF ticked, DWG/NWC/IFC grey.
2. Browse a main folder, initials ANE: "New folder: ...\261019_ANE-   >   PDF".
3. Select 2-3 sheets in the Project Browser first: "Selected in Browser (3 sheets)".
4. Try Pick from list (search, tick/untick) and a Revit Sheet Set.
5. Export: progress bar, then the report. Folder has PDF\ with one file per Sheet
   Number + <model>_261019.pdf.
6. Open a single PDF and the combined one: same look; A1 sheet = A1 page; colour;
   no ref planes / scope boxes / crop lines / unreferenced section marks.
7. Export again: a new folder 261019_ANE-(2).
8. Same test in Revit 2024 if possible.

## 0.2.1 - 2026-11-23 - File names = drawing number + revision
- Akash: file name = drawing number ("/" -> "-") + "-" + revision; revision "-" or
  empty -> one "-"; an empty part of the number stays as it is ("--"). For PDF and CAD.
- Found in the live model (read-only queries, Revit 2024, PRJ01 PIM-0001): the drawing
  number is built from Project Info + 6 sheet parameters + Sheet Number; the title
  block Rev. is Current Revision (3791 = 0.6), not "Revision No".
- icspl_export: drawing_file_name(); plan_sheet_files uses it when a sheet has
  "drawing_no". icspl_revit: PROJECT_PARTS, SHEET_PARTS, drawing_number(),
  current_revision(); collect_sheets adds drawing_no + revision.
- The real code run in the model: 141 sheets -> 141 unique names, none skipped.
- tools/ipy_run.ps1 finds pyRevit 7 (now in %APPDATA%\pyRevit-Master).
- Tests: 16 helper tests (CPython + IronPython), 35 window checks, syntax/API check: pass.
- Note: Revit 2024 closed during the first read-only query (Manage Links dialog was
  open). Reopened by Akash; the next queries ran fine.
- Still waiting: Akash's Revit test of PDF Print (list under 0.2.0).

## 0.3.0 - 2026-11-23 - DWG Export (not yet run in Revit)
- DWG answers: setup picked from the model, one DWG per sheet (views merged, no
  xrefs), AutoCAD 2018, same sheets as PDF.
- icspl_revit: dwg_setups(), dwg_option_values(), dwg_options(), export_dwg(); the
  rename fallback is shared with PDF (_written), for names with a dot (...-0.6).
- Window: "DWG setup" dropdown under the formats (shown when DWG is ticked), DWG line
  in the summary, "dwg_setup" remembered. BUILT_FORMATS = PDF, DWG.
- icspl_run: _run_dwg -> <new folder>\CAD, report (written + sizes, skipped, renamed,
  options Revit refused). DWG Export button now opens the window with DWG ticked.
- Tests: 16 helper, window (DWG checks added), syntax/API (DWGExportOptions): pass.
- Not checked live yet: the model's DWG setup list (Revit was busy with Akash's PDF test).

### Revit test list for DWG Export
1. Reload. DWG Export opens the window with DWG ticked and the "DWG setup" list.
2. Tick PDF too, 2-3 sheets, Export: one new folder with PDF\ and CAD\.
3. CAD file names = PDF file names (e.g. PRJ01-ICSPL-Z01-ZZ-S-STR-DR-DET-3791-0.6.dwg).
4. Open a DWG in AutoCAD: one file, views inside (no xref), layers as the setup.

## 0.3.1 - 2026-11-23 - PDF export setup
- Akash: the PDF export setup was missing. Window: "PDF setup" dropdown (shown when PDF
  is ticked) with the model's ExportPDFSettings; last used, else the active one;
  "pdf_setup" remembered. No setups -> "<ICSPL default>" (the 19 Oct settings).
- With a setup its options are used as saved; only Combine + FileName are set, so the
  file names stay drawing number + revision. Report shows the setup.
- Live check (PRJ01 PIM-0001): setups PDF, PDF_Color, PDF_Color_No Seq, PDF_Mono;
  active PDF_Color = Color, ISO A1, Presentation, zoom 100, vector, hide ref planes ON,
  hide unreferenced view tags OFF. Akash chose B: the 4 hide options are always ON over any setup (R.pdf_hide_values); the setup in the model is not changed.
- Tests pass (window: PDF setup checks added).
- Akash chose B: the 4 hide options are always ON over any PDF setup
  (R.pdf_hide_values). Checked live: PDF_Color export = all 4 hidden, Presentation,
  ISO A1; the PDF_Color setup in the model is unchanged (tags still OFF there).

## 0.4.0 - 2026-11-23 - NWC Export (not yet run in Revit)
- NWC answers: 3D view picked in the window; file = model name; only elements modelled
  in the STR model, nothing linked (no Revit, IFC, CAD, PDF, images); shared
  coordinates; all parameters; not divided by levels; no rooms; visible in the view only.
- icspl_export: nwc_file_name(), choose_view(), NWC_SUMMARY, BUILT_FORMATS + NWC.
- icspl_revit: nwc_available(), views_3d(), nwc_option_values(), nwc_options(),
  linked_in_view(), export_nwc() (links hidden in a rolled-back transaction).
- Window: "NWC 3D view" dropdown (shown when NWC is ticked), NWC needs no sheets,
  "nwc_view" remembered; NWC off with the reason when the exporter is missing.
- icspl_run: _run_nwc -> <new folder>\<model>.nwc, report (file, size, time, view,
  linked items left out, options Revit refused). NWC Export button opens the window.
- Tests: 18 helper, window (NWC checks), syntax/API (NavisworksExportOptions in the
  Revit 2024 DLL): pass.
- Live read-only check (Revit 2026, P200-ICSPL-BLK1-ZZ-S-STR-M3-PIM-0004-): exporter
  installed; 6 3D views; pre-selected = the view named like the model (no links in it);
  the architectural Revit link shows in {3D}, IFC and Analytical Model and would be hidden.

### Revit test list for NWC Export
1. Reload. NWC Export opens the window with NWC ticked and the "NWC 3D view" list.
2. Pick the view, Export: <new folder>\P200-ICSPL-BLK1-ZZ-S-STR-M3-PIM-0004-.nwc.
3. Try the {3D} view too (it shows the architectural link): the report lists the link as left out.
4. Open the NWC in Navisworks: only STR elements, no link, properties on the elements,
   lines up with the other disciplines (shared coordinates).
5. In Revit: the view still shows the link (nothing changed), no new undo step.

## 0.4.1 - 2026-11-23 - Window shows only what the ticked formats use
- Akash (screenshot, NWC only ticked): the Sheets section was shown although NWC does
  not use sheets. Now "3. Sheets" is shown only when PDF or DWG is ticked; without it
  the window shrinks to its content and gets its full size back when PDF/DWG is ticked.
  The setup rows (PDF setup, DWG setup, NWC 3D view) already follow the ticks.
- Window test: checks added, pass.

## 0.5.0 - 2026-11-23 - IFC Export (not yet run in Revit)
- Akash asked if the IFC export settings can be read: yes. The model (P200 PIM-0004)
  has 2 saved setups (DataStorage, schema IFCExportConfigurationMap, JSON):
  "IFC-SG Regulatory Requirements View" (IFC-SG, built-in + saved changes) and
  "IFC Configuration - To Consultant" (IFC2x3 CV2.0).
- IFC answers: always IFC-SG (no dropdown); the same 3D view as NWC; file = model
  name; the missing IFC-SG mapping file (Revit 2024 Program Files path) -> the same
  file from the running Revit's IFC add-in; nothing linked (same rule as NWC).
- icspl_export: IFC_SETUP, IFC_SUMMARY, IFC_MISSING, ifc_file_name(),
  replacement_file(); BUILT_FORMATS = all four.
- icspl_revit: ifc_setup() (Revit's own IFC exporter: built-in + saved setups),
  ifc_prepare() (mapping file, no links, view only), ifc_describe(), ifc_options(),
  export_ifc() (transaction rolled back; links hidden in it).
- Window: one 3D view row for NWC and IFC ("NWC/IFC 3D view"), "IFC setup" row
  (fixed name), IFC off with the reason when the exporter/setup is missing.
- icspl_run: _run_ifc -> <new folder>\<model>.ifc, report (file, size, time, view,
  setup table, notes, linked items left out). IFC Export button opens the window.
- Live read-only check (Revit 2026): setup found; mapping file replaced by
  ...\IFC 2026.bundle\Contents\2026\IFC-SG Property Mapping Export.txt; options
  FileVersion IFCSG, FilterViewId = the picked view; model setup unchanged.
- Tests: 20 helper, window (IFC checks), syntax/API: pass.
- Incident: a crashed inline edit emptied tests\test_icspl_export.py (tests\ is not in
  git yet). Rebuilt from the session's Write/Edit history (16 tests, same lines), then
  the NWC and IFC tests were added again.

### Revit test list for IFC Export
1. Reload. IFC Export opens the window with IFC ticked, "IFC setup: IFC-SG ..." and
   the 3D view list.
2. Export: <new folder>\P200-ICSPL-BLK1-ZZ-S-STR-M3-PIM-0004-.ifc; the report shows
   the setup table and the mapping-file note.
3. Tick NWC + IFC together: both files, the same view.
4. Open the IFC (e.g. in the IFC-SG checker / a viewer): IFC-SG property sets present,
   only STR elements, no link.
5. In Revit: the view and the IFC setup unchanged, no new undo step.

## 0.5.1 - 2026-11-23 - First push to GitHub (public repo)
- The GitHub repo is public. Akash: only the ICSPL name may appear. All client and
  project names in code comments, tests, CLAUDE.md and HISTORY.md were replaced by
  made-up ones (PRJ01, Z01, P200, BLK1, ARCH, "To Consultant", "Authority"). Tests pass.
- Pushed as one new commit on top of GitHub's first commit (README), so the earlier
  local commit with the real names is not online. It stays on this PC only as branch
  backup-with-client-names.

## 0.6.0 - 2026-11-23 - One-line installer for colleagues
- Akash: install like his ERSS tool, with one line pasted in a terminal, which also
  installs pyRevit when missing and updates an older pyRevit to the latest.
- install.ps1 (repo root): pyRevit none -> latest, older -> latest (7.1.0.26319 on
  15 Nov), latest -> left; then ICSPL Export only, into %APPDATA%\ICSPLExport\Extension
  (registered in pyRevit). Again = update. uninstall.ps1 removes ICSPL Export only.
- A PC that already loads ICSPL Export from another folder (the development copy) is
  skipped, so the Export tab never shows twice.
- README: "Install (one line)" section.
- Tests: tests\ps_installer.ps1: both scripts parse in PowerShell 5.1 and 7, ASCII;
  dry run on Akash's PC: pyRevit 7.0.0.26278 -> would update to 7.1.0.26319 (asks to
  close Revit); development copy found -> not installed twice; GitHub ZIP downloaded
  and the extension found (version 8b86a9b).
- Not run for real yet (pyRevit update, copy, registration): first real test on a
  colleague's PC.
