# -*- coding: utf-8 -*-
"""Export window test in pyRevit's IronPython 2.7 engine (no Revit):

    powershell -ExecutionPolicy Bypass -File tools\\ipy_run.ps1 -Py tests\\ipy_window.py

Loads ExportWindow.xaml with made-up sheets and checks the rules, then opens
the window off-screen for a moment and presses Export from a timer.
"""

import datetime
import os
import shutil
import sys
import tempfile

import clr
clr.AddReference("PresentationFramework")
clr.AddReference("PresentationCore")
clr.AddReference("WindowsBase")
from System import TimeSpan, EventHandler
from System.Windows import Visibility, WindowStartupLocation
from System.Windows.Threading import DispatcherTimer

import icspl_window as W

DAY = datetime.date(2026, 10, 19)
SHEETS = [
    {"id": 1, "number": "S-001", "name": "GENERAL NOTES"},
    {"id": 2, "number": "S-101", "name": "FLOOR PLAN AT LANDING 4"},
    {"id": 3, "number": "S-102", "name": "FLOOR PLAN AT LANDING 5"},
    {"id": 4, "number": "S-201", "name": "SECTIONS"},
    {"id": 5, "number": "S-301", "name": "DETAILS"},
]
SETS = [
    {"name": "Issue A", "ids": [1, 3], "other": 2},
    {"name": "Empty set", "ids": [], "other": 0},
]

failures = []


def check(cond, text):
    print("  {0}  {1}".format("ok  " if cond else "FAIL", text))
    if not cond:
        failures.append(text)


def make(selected, settings):
    return W.ExportWindow(SHEETS, selected, SETS, settings, "P200-TEST-MODEL", DAY,
                          start_format="PDF", version_text="Revit 2026")


tmp = tempfile.mkdtemp()
try:
    print("1. Browser selection present")
    w = make([2, 4, 99], {"main_folder": tmp, "initials": "ANE", "sheet_mode": "set", "sheet_set": "Issue A"})
    check(w.mode() == "browser", "starts in Selected in Browser when sheets are selected")
    check(w.chosen_ids() == [2, 4], "chosen = browser selection (99 is not a sheet)")
    check("(2 sheets)" in str(w.rb_browser.Content), "browser radio shows the count")
    check(not w.boxes[0].IsEnabled, "ticks are read-only outside Pick")
    check(w.boxes[1].IsChecked and not w.boxes[0].IsChecked, "list shows the browser ticks")
    check(w.chosen_formats() == ["PDF"], "PDF pre-ticked")
    check(w.chk_ifc.IsEnabled, "IFC can be ticked")
    check(w.chk_nwc.IsEnabled, "NWC can be ticked")
    check(w.chk_dwg.IsEnabled, "DWG can be ticked")
    check(w.sheets_group.Visibility == Visibility.Visible, "PDF ticked -> Sheets section shown")
    check(w.dwg_row.Visibility == Visibility.Collapsed, "DWG setup row hidden while DWG is off")
    check(w.dwg_setup() == "", "no setups in the model -> Revit default")
    w.chk_dwg.IsChecked = True
    check(w.dwg_row.Visibility == Visibility.Visible, "DWG setup row shown when DWG ticked")
    check("CAD" in w.new_folder_text.Text and "DWG:" in w.pdf_text.Text, "preview names CAD, DWG line shown")
    w.chk_dwg.IsChecked = False
    check(w.export_btn.IsEnabled, "Export on")
    check(w.new_folder_path() == os.path.join(tmp, "261019_ANE-"), "new folder 261019_ANE-")
    check("PDF" in w.new_folder_text.Text, "preview names the PDF subfolder")
    check("P200-TEST-MODEL_261019.pdf" in w.pdf_text.Text, "combined name in the PDF line")
    os.makedirs(os.path.join(tmp, "261019_ANE-"))
    w._refresh_status()
    check(w.new_folder_path() == os.path.join(tmp, "261019_ANE-(2)"), "existing folder -> (2)")

    print("2. Sheet Set")
    w.rb_set.IsChecked = True
    check(w.mode() == "set" and w.chosen_ids() == [1, 3], "set Issue A -> sheets 1, 3")
    check("2 views in the set are not sheets" in w.count_text.Text, "non-sheet views reported")
    w.set_combo.SelectedIndex = 1
    check(w.chosen_ids() == [] and "No sheets ticked." in w.problems(), "empty set -> no sheets")
    check(not w.export_btn.IsEnabled, "Export off with no sheets")

    print("3. Pick from list")
    w.rb_pick.IsChecked = True
    check(w.chosen_ids() == [2, 4], "pick list pre-ticked from the browser selection")
    check(w.boxes[0].IsEnabled, "ticks editable in Pick")
    w.boxes[0].IsChecked = True
    check(w.chosen_ids() == [1, 2, 4], "ticking a box adds the sheet")
    w.search_box.Text = "landing"
    visible = [s["id"] for b, s in zip(w.boxes, SHEETS) if b.Visibility == Visibility.Visible]
    check(visible == [2, 3], "search 'landing' shows 2 sheets")
    w._untick_all(None, None)
    check(w.chosen_ids() == [1, 4], "Untick all only touches the visible sheets")
    w._tick_all(None, None)
    check(w.chosen_ids() == [1, 2, 3, 4], "Tick all only touches the visible sheets")
    w.search_box.Text = ""
    check(all(b.Visibility == Visibility.Visible for b in w.boxes), "clear search shows all")

    print("4. Problems")
    w.initials_box.Text = ""
    check("Enter your initials." in w.problems() and not w.export_btn.IsEnabled, "initials required")
    w.initials_box.Text = "A/B"
    check(any("Initials" in p for p in w.problems()), "bad initials refused")
    w.initials_box.Text = "ANE"
    w.folder_box.Text = os.path.join(tmp, "missing")
    check("Main folder not found." in w.problems(), "missing main folder")
    w.folder_box.Text = ""
    check("Pick the main folder." in w.problems(), "empty main folder")
    w.folder_box.Text = tmp
    w.chk_pdf.IsChecked = False
    check("Tick a format." in w.problems() and w.pdf_text.Visibility == Visibility.Collapsed, "no format")
    w.chk_pdf.IsChecked = True
    check(w.problems() == [] and w.export_btn.IsEnabled, "all fixed -> Export on")
    got = w.collect()
    check(got == {"formats": ["PDF"], "main_folder": tmp, "initials": "ANE", "sheet_mode": "pick",
                  "sheet_set": "Empty set", "sheet_ids": [1, 2, 3, 4], "dwg_setup": "",
                  "pdf_setup": "", "nwc_view": ""},
          "collect() " + repr(got))

    print("5. No selection, no sheet sets, saved mode 'browser'")
    w2 = W.ExportWindow(SHEETS, [], [], {"sheet_mode": "browser"}, "M", DAY)
    check(w2.mode() == "pick", "falls back to Pick")
    check(not w2.rb_browser.IsEnabled and not w2.rb_set.IsEnabled, "browser + set radios off")
    check(w2.initials_box.Text == "ANE", "default initials ANE")
    check("No sheets ticked." in w2.problems(), "nothing ticked yet")

    print("5b. DWG setups from the model")
    w4 = W.ExportWindow(SHEETS, [], [], {"dwg_setup": "ICSPL CAD"}, "M", DAY, start_format="DWG",
                        dwg_setups=["A setup", "ICSPL CAD", "Authority"], dwg_active="Authority")
    check(w4.chosen_formats() == ["DWG"], "DWG button -> DWG ticked")
    check(w4.dwg_setup() == "ICSPL CAD", "last used setup remembered")
    w5 = W.ExportWindow(SHEETS, [], [], {}, "M", DAY, dwg_setups=["A setup", "Authority"], dwg_active="Authority")
    check(w5.dwg_setup() == "Authority", "else the model's active setup")

    print("5c. PDF setups from the model")
    w6 = W.ExportWindow(SHEETS, [], [], {}, "M", DAY,
                        pdf_setups=["PDF_Color", "PDF_Grey"], pdf_active="PDF_Color")
    check(w6.pdf_setup() == "PDF_Color", "PDF setup = the model's active one")
    check(w6.pdf_row.Visibility == Visibility.Visible, "PDF setup row shown (PDF ticked)")
    check("Settings from the PDF setup" in w6.pdf_text.Text, "summary says the setup is used")
    w6.pdf_combo.SelectedIndex = 1
    check(w6.collect()["pdf_setup"] == "PDF_Grey", "changed setup is returned")
    w6.chk_pdf.IsChecked = False
    check(w6.pdf_row.Visibility == Visibility.Collapsed, "PDF setup row hidden when PDF is off")
    check(w.pdf_setup() == "" and "Colour, sheet size" in w.pdf_text.Text,
          "no setups -> ICSPL default settings")

    print("5d. NWC")
    views = ["3D WORKING", "IFC", "M", "{3D}"]
    w7 = W.ExportWindow([], [], [], {"main_folder": tmp, "initials": "ANE"}, "M", DAY,
                        start_format="NWC", nwc_views=views)
    check(w7.chosen_formats() == ["NWC"], "NWC button -> NWC ticked")
    check(w7.nwc_view() == "M", "3D view named like the model pre-selected")
    check(w7.nwc_row.Visibility == Visibility.Visible, "NWC view row shown")
    check(w7.problems() == [], "NWC needs no sheets: " + repr(w7.problems()))
    check(w7.sheets_group.Visibility == Visibility.Collapsed, "NWC only -> Sheets section hidden")
    w7.chk_pdf.IsChecked = True
    check(w7.sheets_group.Visibility == Visibility.Visible and w7.Height == 740 and w7.MinHeight == 600,
          "PDF ticked -> Sheets section back, full size")
    w7.chk_pdf.IsChecked = False
    check("M.nwc" in w7.new_folder_text.Text and "NWC:" in w7.pdf_text.Text, "NWC file named in preview")
    w7.nwc_combo.SelectedIndex = 1
    check(w7.collect()["nwc_view"] == "IFC", "picked view returned")
    w8 = W.ExportWindow(SHEETS, [], [], {"nwc_view": "IFC", "formats": ["NWC"]}, "M", DAY,
                        nwc_views=views)
    check(w8.nwc_view() == "IFC", "last used view remembered")
    w9 = W.ExportWindow(SHEETS, [], [], {}, "M", DAY, start_format="NWC", nwc_views=[])
    check("No 3D view for NWC / IFC." in w9.problems(), "no 3D views -> NWC refused")
    w10 = W.ExportWindow(SHEETS, [], [], {}, "M", DAY, start_format="NWC", nwc_views=views,
                         nwc_ok=False, version_text="Revit 2026")
    check(not w10.chk_nwc.IsEnabled and "not installed for Revit 2026" in str(w10.chk_nwc.Content),
          "exporter missing -> NWC off with the reason")

    print("5e. IFC")
    w11 = W.ExportWindow([], [], [], {"main_folder": tmp, "initials": "ANE", "nwc_view": "IFC"}, "M", DAY,
                         start_format="IFC", nwc_views=views)
    check(w11.chosen_formats() == ["IFC"], "IFC button -> IFC ticked")
    check(w11.ifc_row.Visibility == Visibility.Visible and "IFC-SG" in w11.ifc_setup_text.Text,
          "IFC setup row shows IFC-SG")
    check(w11.nwc_row.Visibility == Visibility.Visible and w11.view_label.Text == "IFC 3D view",
          "3D view row shown for IFC")
    check(w11.nwc_view() == "IFC", "same remembered 3D view as NWC")
    check(w11.problems() == [] and w11.sheets_group.Visibility == Visibility.Collapsed,
          "IFC needs no sheets")
    check("M.ifc" in w11.new_folder_text.Text and "IFC:" in w11.pdf_text.Text, "IFC file named in preview")
    w11.chk_nwc.IsChecked = True
    check(w11.view_label.Text == "NWC/IFC 3D view", "one 3D view for NWC + IFC")
    check(w11.collect()["formats"] == ["NWC", "IFC"], "both formats returned")
    w12 = W.ExportWindow(SHEETS, [], [], {}, "M", DAY, start_format="IFC", nwc_views=views,
                         ifc_reason="IFC setup 'X' not found")
    check(not w12.chk_ifc.IsEnabled and "not found" in str(w12.chk_ifc.Content),
          "IFC off with the reason when the setup is missing")

    print("6. Open the window, Export from a timer")
    w3 = make([], {"main_folder": tmp, "initials": "ANE", "formats": ["PDF"]})
    w3.WindowStartupLocation = WindowStartupLocation.Manual
    w3.Left, w3.Top = -3000, -3000
    w3.ShowActivated = False

    def press_export(sender, args):
        sender.Stop()
        w3.boxes[2].IsChecked = True
        w3._export(None, None)

    def give_up(sender, args):
        sender.Stop()
        w3.Close()

    for delay, handler in ((300, press_export), (5000, give_up)):
        t = DispatcherTimer()
        t.Interval = TimeSpan.FromMilliseconds(delay)
        t.Tick += EventHandler(handler)
        t.Start()
    res = w3.show()
    check(res is not None and res["sheet_ids"] == [3], "show() returns the choice: " + repr(res))
finally:
    shutil.rmtree(tmp)

print("")
print("{0} failure(s)".format(len(failures)))
sys.exit(1 if failures else 0)
