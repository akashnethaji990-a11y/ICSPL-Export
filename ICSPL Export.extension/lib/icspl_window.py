# -*- coding: utf-8 -*-
"""Export window shared by the buttons (IronPython 2.7).

No Revit API here: it gets plain data (sheets as dicts, sheet sets, saved
settings) and returns the choices, so it can be tested outside Revit
(tools/ipy_run.ps1 + tests/ipy_window.py).

sheets:      [{"id": int, "number": str, "name": str}, ...] in display order
selected_ids: sheet ids selected in the Project Browser
sheet_sets:  [{"name": str, "ids": [int], "other": int}, ...]
             (other = views in the set that are not sheets)
nwc_views:   names of the 3D views for NWC and IFC (one choice for both, Akash)
nwc_ok:      False when the NWC exporter is not installed for this Revit
ifc_reason:  "" when IFC can run, else why not (exporter or setup missing)
"""

import os

import clr
clr.AddReference("PresentationFramework")
clr.AddReference("PresentationCore")
clr.AddReference("WindowsBase")
clr.AddReference("System.Xaml")
clr.AddReference("System.Windows.Forms")

try:
    import wpf
except ImportError:
    # inside pyRevit the wpf module is loaded by pyrevit.framework
    from pyrevit.framework import wpf

import System.Windows.Forms as WinForms
from System.Windows import Window, Visibility, Thickness, SizeToContent
from System.Windows.Controls import CheckBox
from System.Windows.Interop import WindowInteropHelper

import icspl_export as X

XAML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ExportWindow.xaml")

DEFAULT_INITIALS = "ANE"


class ExportWindow(Window):
    def __init__(self, sheets, selected_ids, sheet_sets, settings, model_name, today,
                 start_format="PDF", owner_handle=None, version_text="",
                 dwg_setups=None, dwg_active="", pdf_setups=None, pdf_active="",
                 nwc_views=None, nwc_ok=True, ifc_reason=""):
        wpf.LoadComponent(self, XAML_PATH)
        self._busy = False
        self._full_height = self.Height
        self._full_min = self.MinHeight
        self.result = None
        self.today = today
        self.model_name = model_name
        self.sheets = list(sheets)
        self.order = [s["id"] for s in self.sheets]
        valid = set(self.order)
        self.selected = set(i for i in selected_ids if i in valid)
        self.picked = set(self.selected)
        self.sheet_sets = list(sheet_sets)
        if owner_handle:
            WindowInteropHelper(self).Owner = owner_handle

        info = [u"Model: {0}".format(model_name), u"{0} sheets".format(len(self.sheets))]
        if version_text:
            info.insert(1, version_text)
        self.model_text.Text = u"   |   ".join(info)

        self.version_text = version_text
        self.nwc_ok = nwc_ok
        self.ifc_reason = ifc_reason
        self.ifc_setup_text.Text = X.IFC_SETUP
        self._setup_formats(settings, start_format)
        self.dwg_setups = self._fill_setups(self.dwg_combo, dwg_setups, dwg_active,
                                            settings.get("dwg_setup", ""), X.DWG_DEFAULT_SETUP)
        self.pdf_setups = self._fill_setups(self.pdf_combo, pdf_setups, pdf_active,
                                            settings.get("pdf_setup", ""), X.PDF_DEFAULT_SETUP)
        self.nwc_views = list(nwc_views or [])
        pick = X.choose_view(self.nwc_views, settings.get("nwc_view", ""), model_name)
        for name in self.nwc_views:
            self.nwc_combo.Items.Add(name)
        if pick:
            self.nwc_combo.SelectedIndex = self.nwc_views.index(pick)
        self.nwc_combo.SelectionChanged += self._status_changed
        self.folder_box.Text = settings.get("main_folder", "")
        self.initials_box.Text = settings.get("initials", DEFAULT_INITIALS)
        self._setup_sources(settings)
        self._setup_sheet_list()

        self.folder_box.TextChanged += self._status_changed
        self.initials_box.TextChanged += self._status_changed
        self.browse_btn.Click += self._browse
        self.rb_pick.Checked += self._sheets_changed
        self.rb_browser.Checked += self._sheets_changed
        self.rb_set.Checked += self._sheets_changed
        self.set_combo.SelectionChanged += self._sheets_changed
        self.search_box.TextChanged += self._filter
        self.all_btn.Click += self._tick_all
        self.none_btn.Click += self._untick_all
        self.export_btn.Click += self._export

        self._refresh_sheets()

    # ------------------------------------------------------------ set-up

    def _format_boxes(self):
        return [("PDF", self.chk_pdf), ("DWG", self.chk_dwg),
                ("NWC", self.chk_nwc), ("IFC", self.chk_ifc)]

    def _setup_formats(self, settings, start_format):
        saved = settings.get("formats") or []
        for fmt, box in self._format_boxes():
            if fmt == "NWC" and not self.nwc_ok:
                box.Content = X.NWC_MISSING.format(self.version_text or "this Revit")
                box.IsChecked = False
                box.IsEnabled = False
            elif fmt == "IFC" and self.ifc_reason:
                box.Content = X.IFC_MISSING.format(self.ifc_reason)
                box.IsChecked = False
                box.IsEnabled = False
            elif fmt in X.BUILT_FORMATS:
                box.IsChecked = fmt == start_format or fmt in saved
            else:
                box.Content = "{0} (not built yet)".format(box.Content)
                box.IsChecked = False
                box.IsEnabled = False
            box.Checked += self._status_changed
            box.Unchecked += self._status_changed

    def _fill_setups(self, combo, setups, active, last, default_label):
        """Setup dropdown: the model's setups (last used, else active, else first).
        No setups -> one default_label item. Returns the setup names."""
        names = list(setups or [])
        if not names:
            combo.Items.Add(default_label)
            combo.SelectedIndex = 0
            return names
        for name in names:
            combo.Items.Add(name)
        pick = last if last in names else (active if active in names else names[0])
        combo.SelectedIndex = names.index(pick)
        return names

    @staticmethod
    def _chosen(combo, names):
        idx = combo.SelectedIndex
        return names[idx] if 0 <= idx < len(names) else ""

    def dwg_setup(self):
        """Chosen DWG setup name ("" = Revit default)."""
        return self._chosen(self.dwg_combo, self.dwg_setups)

    def pdf_setup(self):
        """Chosen PDF setup name ("" = the ICSPL default settings)."""
        return self._chosen(self.pdf_combo, self.pdf_setups)

    def nwc_view(self):
        """Chosen 3D view name for NWC and IFC ("" = none)."""
        return self._chosen(self.nwc_combo, self.nwc_views)

    def _setup_sources(self, settings):
        n_sel = len(self.selected)
        self.rb_browser.Content = "Selected in Browser ({0} sheet{1})".format(n_sel, "" if n_sel == 1 else "s")
        self.rb_browser.IsEnabled = n_sel > 0

        for s in self.sheet_sets:
            self.set_combo.Items.Add(u"{0}   ({1} sheets)".format(s["name"], len(s["ids"])))
        if self.sheet_sets:
            names = [s["name"] for s in self.sheet_sets]
            last = settings.get("sheet_set", "")
            self.set_combo.SelectedIndex = names.index(last) if last in names else 0
        else:
            self.rb_set.Content = "Revit Sheet Set (none in this model)"
            self.rb_set.IsEnabled = False
            self.set_combo.IsEnabled = False

        mode = settings.get("sheet_mode", "pick")
        if self.selected:
            mode = "browser"
        elif mode not in X.SHEET_MODES or mode == "browser" or (mode == "set" and not self.sheet_sets):
            mode = "pick"
        {"pick": self.rb_pick, "browser": self.rb_browser, "set": self.rb_set}[mode].IsChecked = True

    def _setup_sheet_list(self):
        self.boxes = []
        for s in self.sheets:
            box = CheckBox()
            box.Content = u"{0}    {1}".format(s["number"], s["name"])
            box.Margin = Thickness(0, 1, 0, 1)
            box.Checked += self._ticked
            box.Unchecked += self._ticked
            self.sheet_panel.Children.Add(box)
            self.boxes.append(box)

    # ------------------------------------------------------------ state

    def mode(self):
        if self.rb_browser.IsChecked:
            return "browser"
        if self.rb_set.IsChecked:
            return "set"
        return "pick"

    def current_set(self):
        idx = self.set_combo.SelectedIndex
        if 0 <= idx < len(self.sheet_sets):
            return self.sheet_sets[idx]
        return None

    def chosen_formats(self):
        return [fmt for fmt, box in self._format_boxes() if box.IsChecked and box.IsEnabled]

    def chosen_ids(self):
        """Ids of the sheets to export, in display order."""
        mode = self.mode()
        if mode == "browser":
            wanted = self.selected
        elif mode == "set":
            cur = self.current_set()
            wanted = set(cur["ids"]) if cur else set()
        else:
            wanted = self.picked
        return [i for i in self.order if i in wanted]

    def new_folder_path(self):
        """Full path of the new dated folder, or '' while folder/initials are not usable."""
        main = self.folder_box.Text.strip()
        initials = self.initials_box.Text.strip()
        if not main or not os.path.isdir(main) or X.initials_problem(initials):
            return ""
        name = X.next_free_name(X.issue_folder_base(self.today, initials),
                                lambda n: os.path.exists(os.path.join(main, n)))
        return os.path.join(main, name)

    @staticmethod
    def needs_sheets(formats):
        """Sheets are used by PDF and DWG only (NWC / IFC export a 3D view)."""
        return "PDF" in formats or "DWG" in formats

    @staticmethod
    def needs_view(formats):
        """NWC and IFC export one 3D view (the same one, Akash)."""
        return "NWC" in formats or "IFC" in formats

    def _show_sheets(self, show):
        """Sheets section only when a sheet format is ticked (Akash, 23 Nov); without it
        the window shrinks to its content, and gets its old height back after."""
        visible = self.sheets_group.Visibility == Visibility.Visible
        if show == visible:
            return
        if show:
            self.sheets_group.Visibility = Visibility.Visible
            self.SizeToContent = SizeToContent.Manual
            self.MinHeight = self._full_min
            self.Height = max(self._full_height, self._full_min)
        else:
            self._full_height = self.ActualHeight if self.ActualHeight > 0 else self.Height
            self.sheets_group.Visibility = Visibility.Collapsed
            self.MinHeight = 0
            self.SizeToContent = SizeToContent.Height

    def problems(self):
        """Reasons the Export button is off (empty list = ready)."""
        out = []
        formats = self.chosen_formats()
        if not formats:
            out.append("Tick a format.")
        main = self.folder_box.Text.strip()
        if not main:
            out.append("Pick the main folder.")
        elif not os.path.isdir(main):
            out.append("Main folder not found.")
        initials = X.initials_problem(self.initials_box.Text)
        if initials:
            out.append(initials)
        if self.needs_sheets(formats) and not self.chosen_ids():
            out.append("No sheets ticked.")
        if self.needs_view(formats) and not self.nwc_view():
            out.append("No 3D view for NWC / IFC." if not self.nwc_views else "Pick the 3D view.")
        return out

    def collect(self):
        """The choices as a dict (what Export returns)."""
        cur = self.current_set()
        return {
            "formats": self.chosen_formats(),
            "main_folder": self.folder_box.Text.strip(),
            "initials": self.initials_box.Text.strip(),
            "sheet_mode": self.mode(),
            "sheet_set": cur["name"] if cur else "",
            "sheet_ids": self.chosen_ids(),
            "dwg_setup": self.dwg_setup(),
            "pdf_setup": self.pdf_setup(),
            "nwc_view": self.nwc_view(),
        }

    # ------------------------------------------------------------ refresh

    def _refresh_sheets(self):
        if self._busy:
            return
        self._busy = True
        try:
            mode = self.mode()
            wanted = set(self.chosen_ids())
            editable = mode == "pick"
            for box, s in zip(self.boxes, self.sheets):
                box.IsChecked = s["id"] in wanted
                box.IsEnabled = editable
            self.all_btn.IsEnabled = editable
            self.none_btn.IsEnabled = editable
            self.set_combo.IsEnabled = mode == "set"
            text = "{0} of {1} sheets will be exported".format(len(wanted), len(self.sheets))
            cur = self.current_set()
            if mode == "set" and cur and cur.get("other"):
                text += "  ({0} views in the set are not sheets, left out)".format(cur["other"])
            if not editable:
                text += "  (to change the ticks use Pick from list)"
            self.count_text.Text = text
        finally:
            self._busy = False
        self._refresh_status()

    def _refresh_status(self):
        formats = self.chosen_formats()
        path = self.new_folder_path()
        if path:
            subs = []
            if "PDF" in formats:
                subs.append(X.PDF_FOLDER)
            if "DWG" in formats:
                subs.append(X.CAD_FOLDER)
            if "NWC" in formats:
                subs.append(X.nwc_file_name(self.model_name) + ".nwc")
            if "IFC" in formats:
                subs.append(X.ifc_file_name(self.model_name) + ".ifc")
            self.new_folder_text.Text = u"New folder: {0}{1}".format(
                path, (u"   >   " + u", ".join(subs)) if subs else u"")
        else:
            self.new_folder_text.Text = "New folder: (pick the main folder and enter your initials)"
        lines = []
        if "PDF" in formats:
            lines.append(X.PDF_SUMMARY.format(
                X.combined_pdf_name(self.model_name, self.today) + ".pdf",
                X.PDF_SETUP_NOTE if self.pdf_setup() else X.PDF_DEFAULT_NOTE))
        if "DWG" in formats:
            lines.append(X.DWG_SUMMARY)
        if "NWC" in formats:
            lines.append(X.NWC_SUMMARY.format(X.nwc_file_name(self.model_name) + ".nwc"))
        if "IFC" in formats:
            lines.append(X.IFC_SUMMARY.format(X.ifc_file_name(self.model_name) + ".ifc"))
        self.pdf_text.Text = u"\n".join(lines)
        self.pdf_text.Visibility = Visibility.Visible if lines else Visibility.Collapsed
        self.dwg_row.Visibility = Visibility.Visible if "DWG" in formats else Visibility.Collapsed
        self.pdf_row.Visibility = Visibility.Visible if "PDF" in formats else Visibility.Collapsed
        self.nwc_row.Visibility = Visibility.Visible if self.needs_view(formats) else Visibility.Collapsed
        self.view_label.Text = "/".join(f for f in ("NWC", "IFC") if f in formats) + " 3D view"
        self.ifc_row.Visibility = Visibility.Visible if "IFC" in formats else Visibility.Collapsed
        self._show_sheets(self.needs_sheets(formats))
        problems = self.problems()
        self.status_text.Text = "   ".join(problems)
        self.export_btn.IsEnabled = not problems

    # ------------------------------------------------------------ events

    def _status_changed(self, sender, args):
        self._refresh_status()

    def _sheets_changed(self, sender, args):
        self._refresh_sheets()

    def _ticked(self, sender, args):
        if self._busy or self.mode() != "pick":
            return
        self.picked = set(s["id"] for box, s in zip(self.boxes, self.sheets) if box.IsChecked)
        self._refresh_sheets()

    def _set_visible(self, value):
        for box, s in zip(self.boxes, self.sheets):
            if box.Visibility == Visibility.Visible:
                if value:
                    self.picked.add(s["id"])
                else:
                    self.picked.discard(s["id"])
        self._refresh_sheets()

    def _tick_all(self, sender, args):
        self._set_visible(True)

    def _untick_all(self, sender, args):
        self._set_visible(False)

    def _filter(self, sender, args):
        terms = self.search_box.Text.lower().split()
        for box, s in zip(self.boxes, self.sheets):
            text = u"{0} {1}".format(s["number"], s["name"]).lower()
            visible = all(t in text for t in terms)
            box.Visibility = Visibility.Visible if visible else Visibility.Collapsed

    def _browse(self, sender, args):
        dlg = WinForms.FolderBrowserDialog()
        dlg.Description = "Main folder for the export (a new dated folder is made inside it)"
        dlg.ShowNewFolderButton = True
        current = self.folder_box.Text.strip()
        if os.path.isdir(current):
            dlg.SelectedPath = current
        if dlg.ShowDialog() == WinForms.DialogResult.OK:
            self.folder_box.Text = dlg.SelectedPath

    def _export(self, sender, args):
        if self.problems():
            self._refresh_status()
            return
        self.result = self.collect()
        self.DialogResult = True

    # ------------------------------------------------------------ run

    def show(self):
        """Open as a modal dialog. Returns collect() on Export, None on Cancel."""
        self.ShowDialog()
        return self.result
