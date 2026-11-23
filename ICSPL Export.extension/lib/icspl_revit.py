# -*- coding: utf-8 -*-
"""Revit API side of ICSPL Export (IronPython 2.7, Revit 2024-2026).

The PDF API (PDFExportOptions, Document.Export(folder, ids, options)) and the
DWG API (ExportDWGSettings, DWGExportOptions, Document.Export(folder, name, ids,
options)) and the NWC API (NavisworksExportOptions, Document.Export(folder, name,
options)) are the same in 2024, 2025 and 2026 (checked against each RevitAPI.dll).
IFC uses Revit's own IFC exporter add-in (IFCExporterUIOverride.dll), so a setup is
applied exactly as Revit's IFC dialog applies it.
"""

import os

import clr
clr.AddReference("RevitAPI")
from System.Collections.Generic import List
from Autodesk.Revit.DB import (
    ACADVersion,
    BuiltInParameter,
    ColorDepthType,
    DWGExportOptions,
    ElementId,
    ExportDWGSettings,
    ExportPaperFormat,
    ExportPDFSettings,
    FilteredElementCollector,
    IFCExportOptions,
    ImportInstance,
    ModelPathUtils,
    NavisworksCoordinates,
    NavisworksExportOptions,
    NavisworksExportScope,
    NavisworksParameters,
    OptionalFunctionalityUtils,
    PaperPlacementType,
    PDFExportOptions,
    PointCloudInstance,
    RasterQualityType,
    RevitLinkInstance,
    Transaction,
    View3D,
    ViewSheet,
    ViewSheetSet,
    ZoomType,
)

import icspl_export as X


# ---------------------------------------------------------------- model

def model_name(doc):
    """Model name without .rvt. For a workshared model: the central model's
    name, not the local copy's (which has _<username> added)."""
    path = ""
    try:
        if doc.IsWorkshared:
            central = doc.GetWorksharingCentralModelPath()
            if central is not None:
                path = ModelPathUtils.ConvertModelPathToUserVisiblePath(central)
    except Exception:
        path = ""
    name = X.model_name_from_path(path) or X.model_name_from_path(doc.PathName)
    return name or X.model_name_from_path(doc.Title)


# Drawing number = these values joined by "/", as the title block shows it
# (checked on PRJ01 PIM-0001, 23 Nov: 141 sheets, no duplicates):
# PRJ01 / ICSPL / Z01 / ZZ / S / STR / DR / DET / 3791
PROJECT_PARTS = ("Project Number", "Organization Name")          # Project Information
SHEET_PARTS = ("Project Location Code", "Zone/Level", "Role",     # sheet parameters
               "Discipline", "Type Code", "Sub-Type")             # + Sheet Number last


def _text(element, name):
    param = element.LookupParameter(name)
    if param is None:
        return ""
    return (param.AsString() or param.AsValueString() or "").strip()


def drawing_number(sheet, project_parts):
    """PRJ01/ICSPL/Z01/ZZ/S/STR/DR/DET/3791. An empty part stays empty (Akash: not edited)."""
    parts = list(project_parts) + [_text(sheet, n) for n in SHEET_PARTS] + [sheet.SheetNumber or ""]
    return "/".join(parts)


def current_revision(sheet):
    """Revit's Current Revision of the sheet ("" if none)."""
    param = sheet.get_Parameter(BuiltInParameter.SHEET_CURRENT_REVISION)
    return (param.AsString() or "").strip() if param is not None else ""


def collect_sheets(doc):
    """Printable sheets as dicts sorted by Sheet Number.

    {"id", "number", "name", "drawing_no", "revision", "eid"}
    Placeholder sheets are left out (they cannot be exported).
    """
    info = doc.ProjectInformation
    project_parts = [_text(info, n) for n in PROJECT_PARTS]
    sheets = []
    for sheet in FilteredElementCollector(doc).OfClass(ViewSheet):
        if sheet.IsPlaceholder or not sheet.CanBePrinted:
            continue
        sheets.append({
            "id": int(X.element_id_value(sheet.Id)),
            "number": sheet.SheetNumber or "",
            "name": sheet.Name or "",
            "drawing_no": drawing_number(sheet, project_parts),
            "revision": current_revision(sheet),
            "eid": sheet.Id,
        })
    sheets.sort(key=lambda s: X.natural_key(s["number"]))
    return sheets


def browser_selected_ids(uidoc, valid_ids):
    """Ids of the selected elements that are sheets in valid_ids."""
    out = []
    for eid in uidoc.Selection.GetElementIds():
        value = int(X.element_id_value(eid))
        if value in valid_ids:
            out.append(value)
    return out


def sheet_sets(doc, valid_ids):
    """Saved View/Sheet Sets: [{"name", "ids", "other"}] sorted by name."""
    out = []
    for vss in FilteredElementCollector(doc).OfClass(ViewSheetSet):
        ids, other = [], 0
        for view in vss.Views:
            value = int(X.element_id_value(view.Id))
            if isinstance(view, ViewSheet) and value in valid_ids:
                ids.append(value)
            else:
                other += 1
        out.append({"name": vss.Name, "ids": ids, "other": other})
    out.sort(key=lambda s: s["name"].lower())
    return out


# ---------------------------------------------------------------- PDF

def pdf_option_values():
    """[(PDFExportOptions property, value)] from Akash's Step 2 answers, set in this order."""
    return [
        ("ColorDepth", ColorDepthType.Color),
        ("PaperFormat", ExportPaperFormat.Default),      # = use the sheet size
        ("PaperPlacement", PaperPlacementType.Center),
        ("ZoomType", ZoomType.Zoom),
        ("ZoomPercentage", 100),
        ("RasterQuality", RasterQualityType.High),
        ("AlwaysUseRaster", False),                      # vector
        ("HideReferencePlane", True),                    # reference + work planes
        ("HideScopeBoxes", True),
        ("HideCropBoundaries", True),
        ("HideUnreferencedViewTags", True),              # sections, elevations, callouts
        ("StopOnError", False),
    ]


def pdf_hide_values():
    """Always hidden, also over a PDF setup (Akash, 23 Nov: option B)."""
    return [(name, value) for name, value in pdf_option_values() if name.startswith("Hide")]


def pdf_setups(doc):
    """(PDF export setup names sorted, name of the active setup or "")."""
    names = sorted(ExportPDFSettings.ListNames(doc), key=lambda n: n.lower())
    active = ""
    try:
        setting = ExportPDFSettings.GetActivePredefinedSettings(doc)
        if setting is not None:
            active = setting.Name
    except Exception:
        active = ""
    return list(names), active


def pdf_options(doc=None, setup_name=""):
    """(PDFExportOptions, failed).

    With a setup (Akash, 23 Nov): the setup's options, plus pdf_hide_values() always
    on; Combine and FileName are set at export, so the setup's own naming rule is
    not used. GetOptions() is a copy: the setup in the model is not changed.
    Without one: pdf_option_values().
    The same object is used for the single sheets and the combined file, so
    both have the same content. failed = [(property, error)] not set.
    """
    setting = ExportPDFSettings.FindByName(doc, setup_name) if (doc is not None and setup_name) else None
    if setting is not None:
        options = setting.GetOptions()
        return options, X.set_options(options, pdf_hide_values())
    options = PDFExportOptions()
    failed = X.set_options(options, pdf_option_values())
    return options, failed


def _written(folder, before, file_name, ext, ok, error):
    """(path, "") or (None, reason) after an export call.

    Names like ...-3791-0.6 have a dot, so Revit may cut the name at it. If the
    expected file is missing and exactly one new file with ext appeared, it is
    renamed to the expected name.
    """
    expected = os.path.join(folder, file_name + ext)
    if not os.path.isfile(expected):
        new = [n for n in os.listdir(folder) if n not in before and n.lower().endswith(ext)]
        if len(new) == 1:
            try:
                os.rename(os.path.join(folder, new[0]), expected)
            except Exception as ex:
                error = error or "Revit wrote {0}, rename failed: {1}".format(new[0], ex)
    if os.path.isfile(expected):
        return expected, ""
    if error:
        return None, error
    return None, "Revit did not write the file" if not ok else "file not found after export"


def export_pdf(doc, folder, eids, file_name, options):
    """Export the views to one PDF: folder\\file_name.pdf. Returns (path, "") or (None, reason)."""
    before = set(os.listdir(folder))
    options.Combine = True
    options.FileName = file_name
    error = ""
    ok = False
    try:
        ok = doc.Export(folder, List[ElementId](eids), options)
    except Exception as ex:
        error = str(ex)
    return _written(folder, before, file_name, ".pdf", ok, error)


# ---------------------------------------------------------------- DWG

def dwg_setups(doc):
    """(setup names sorted, name of the active setup or "")."""
    names = sorted(ExportDWGSettings.ListNames(doc), key=lambda n: n.lower())
    active = ""
    try:
        setting = ExportDWGSettings.GetActivePredefinedSettings(doc)
        if setting is not None:
            active = setting.Name
    except Exception:
        active = ""
    return list(names), active


def dwg_option_values():
    """[(DWGExportOptions property, value)] from Akash's DWG answers, set after the setup."""
    return [
        ("MergedViews", True),                 # one DWG per sheet, no xref files
        ("FileVersion", ACADVersion.R2018),
    ]


def dwg_options(doc, setup_name):
    """(DWGExportOptions, failed): the named setup's layers/colours + dwg_option_values().

    setup_name "" or not found = Revit's default options.
    """
    setting = ExportDWGSettings.FindByName(doc, setup_name) if setup_name else None
    options = setting.GetDWGExportOptions() if setting is not None else DWGExportOptions()
    failed = X.set_options(options, dwg_option_values())
    return options, failed


def export_dwg(doc, folder, eid, file_name, options):
    """Export one sheet to folder\\file_name.dwg. Returns (path, "") or (None, reason)."""
    before = set(os.listdir(folder))
    error = ""
    ok = False
    try:
        ok = doc.Export(folder, file_name, List[ElementId]([eid]), options)
    except Exception as ex:
        error = str(ex)
    return _written(folder, before, file_name, ".dwg", ok, error)


# ---------------------------------------------------------------- NWC

def nwc_available():
    """True when the Navisworks NWC Export Utility is installed for this Revit year."""
    try:
        return bool(OptionalFunctionalityUtils.IsNavisworksExporterAvailable())
    except Exception:
        return False


def views_3d(doc):
    """3D views that can be exported (no templates): [{"id", "name", "eid"}] sorted by name."""
    out = []
    for view in FilteredElementCollector(doc).OfClass(View3D):
        if view.IsTemplate:
            continue
        out.append({"id": int(X.element_id_value(view.Id)), "name": view.Name or "", "eid": view.Id})
    out.sort(key=lambda v: X.natural_key(v["name"]))
    return out


def nwc_option_values(view_id):
    """[(NavisworksExportOptions property, value)] from Akash's NWC answers (23 Nov)."""
    return [
        ("ExportScope", NavisworksExportScope.View),     # only what the 3D view shows
        ("ViewId", view_id),
        ("ExportLinks", False),                          # no Revit / IFC links
        ("ConvertLinkedCADFormats", False),              # no linked CAD
        ("Coordinates", NavisworksCoordinates.Shared),
        ("Parameters", NavisworksParameters.All),
        ("ConvertElementProperties", True),
        ("ExportElementIds", True),
        ("DivideFileIntoLevels", False),
        ("ExportRoomGeometry", False),
        ("ExportRoomAsAttribute", False),
        ("ExportParts", False),
        ("ExportUrls", True),
        ("FindMissingMaterials", True),
        ("ConvertLights", False),
    ]


def nwc_options(view_id):
    """(NavisworksExportOptions, failed)."""
    options = NavisworksExportOptions()
    return options, X.set_options(options, nwc_option_values(view_id))


def _image_class():
    try:
        from Autodesk.Revit.DB import ImageInstance     # Revit 2020+
        return ImageInstance
    except ImportError:
        return None


def linked_in_view(doc, view):
    """Linked / imported items visible in the view: [(ElementId, kind, name)].

    Revit links (also IFC links), CAD links and imports, point clouds and images
    (PDF / raster). Only elements modelled in the STR model go to the NWC (Akash).
    """
    kinds = [(RevitLinkInstance, "Revit / IFC link"), (ImportInstance, "CAD link / import"),
             (PointCloudInstance, "Point cloud")]
    image = _image_class()
    if image is not None:
        kinds.append((image, "PDF / image"))
    out = []
    for cls, kind in kinds:
        try:
            found = list(FilteredElementCollector(doc, view.Id).OfClass(cls))
        except Exception:
            continue
        for el in found:
            try:
                if el.IsHidden(view) or not el.CanBeHidden(view):
                    continue
            except Exception:
                continue
            name = ""
            try:
                name = el.Name or ""
            except Exception:
                pass
            out.append((el.Id, kind, name))
    return out


def export_nwc(doc, folder, file_name, view, options):
    """Export the 3D view to folder\\file_name.nwc with every linked item hidden.

    The hiding is done in a transaction that is rolled back after the export, so
    the view and the model are not changed. If Revit refuses to export inside that
    transaction, the items are hidden, exported and shown again (two undo steps).
    Returns (path, "", hidden, note) or (None, reason, hidden, note);
    hidden = [(kind, name)] of the items left out.
    """
    items = linked_in_view(doc, view)
    ids = List[ElementId]([i for i, _, _ in items])
    hidden = [(kind, name) for _, kind, name in items]
    before = set(os.listdir(folder))
    note = ""

    def run_export():
        return doc.Export(folder, file_name, options)

    ok, error = False, ""   # the NWC Export call returns nothing: the file is checked
    if not items:
        try:
            ok = run_export()
        except Exception as ex:
            error = str(ex)
        path, reason = _written(folder, before, file_name, ".nwc", ok, error)
        return path, reason, hidden, note

    t = Transaction(doc, "ICSPL Export: hide links for NWC")
    try:
        t.Start()
        view.HideElements(ids)
        doc.Regenerate()
    except Exception as ex:
        if t.HasStarted() and not t.HasEnded():
            t.RollBack()
        # could not hide (e.g. the view is borrowed by someone else): links and CAD
        # are still left out by the options; PDFs / images / point clouds may show
        note = "Could not hide the linked items in the view ({0}).".format(ex)
        try:
            ok = run_export()
        except Exception as ex2:
            error = str(ex2)
        path, reason = _written(folder, before, file_name, ".nwc", ok, error)
        return path, reason, [], note
    try:
        ok = run_export()
    except Exception as ex:
        error = str(ex)
    finally:
        t.RollBack()

    if not nwc_appeared(folder, before):
        # second way: hide (committed), export, show again
        error = ""
        t1 = Transaction(doc, "ICSPL Export: hide links for NWC")
        t1.Start()
        view.HideElements(ids)
        t1.Commit()
        try:
            ok = run_export()
        except Exception as ex:
            error = str(ex)
        finally:
            t2 = Transaction(doc, "ICSPL Export: show links again")
            t2.Start()
            view.UnhideElements(ids)
            t2.Commit()
        note = "Exported with the links hidden and then shown again (2 undo steps)."
    path, reason = _written(folder, before, file_name, ".nwc", ok, error)
    return path, reason, hidden, note


def nwc_appeared(folder, before):
    """True when a new .nwc file appeared in folder since `before`."""
    return any(n not in before and n.lower().endswith(".nwc") for n in os.listdir(folder))


# ---------------------------------------------------------------- IFC

IFC_UI_ASSEMBLY = "IFCExporterUIOverride"


def _ifc_ui_assembly(application):
    """Revit's IFC exporter UI assembly: the loaded one, else from the IFC add-in
    folders of the running Revit year. None if not found."""
    import System
    for asm in System.AppDomain.CurrentDomain.GetAssemblies():
        if asm.GetName().Name == IFC_UI_ASSEMBLY:
            return asm
    year = str(X.revit_year(application))
    program_data = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    candidates = [
        os.path.join(program_data, "Autodesk", "ApplicationPlugins", "IFC {0}.bundle".format(year),
                     "Contents", year, IFC_UI_ASSEMBLY + ".dll"),
    ]
    try:
        exe_dir = os.path.dirname(System.Diagnostics.Process.GetCurrentProcess().MainModule.FileName)
        candidates.append(os.path.join(exe_dir, "AddIns", "IFCExporterUI", IFC_UI_ASSEMBLY + ".dll"))
    except Exception:
        pass
    for path in candidates:
        if os.path.isfile(path):
            try:
                return System.Reflection.Assembly.LoadFrom(path)
            except Exception:
                continue
    return None


def ifc_setup(doc, application, name):
    """(configuration, exporter folder, reason).

    The named IFC setup as Revit's IFC dialog sees it: the built-in setups plus the
    ones saved in the model (IFCExportConfigurationsMap). configuration is a copy, so
    changing it does not change the setup in the model. (None, "", reason) if the
    exporter or the setup is not found.
    """
    asm = _ifc_ui_assembly(application)
    if asm is None:
        return None, "", "Revit's IFC exporter add-in was not found"
    try:
        clr.AddReference(asm)
        from BIM.IFC.Export.UI import IFCCommandOverrideApplication, IFCExportConfigurationsMap
    except Exception as ex:
        return None, "", "IFC exporter could not be loaded ({0})".format(ex)
    folder = os.path.dirname(asm.Location)
    old = IFCCommandOverrideApplication.TheDocument
    IFCCommandOverrideApplication.TheDocument = doc     # AddSavedConfigurations reads this
    try:
        setups = IFCExportConfigurationsMap()
        setups.AddBuiltInConfigurations()
        setups.AddSavedConfigurations()
        if not setups.HasName(name):
            return None, folder, "IFC setup '{0}' not found".format(name)
        return setups[name].Clone(), folder, ""
    except Exception as ex:
        return None, folder, "IFC setups could not be read ({0})".format(ex)
    finally:
        IFCCommandOverrideApplication.TheDocument = old


def ifc_prepare(config, exporter_folder):
    """Akash's IFC rules on the copy of the setup. Returns notes for the report.

    - missing mapping files -> the same file from the running Revit's IFC add-in;
    - linked files never exported; only what the picked 3D view shows.
    """
    import System
    notes = []
    for flag, prop in (("ExportUserDefinedPsets", "ExportUserDefinedPsetsFileName"),
                       ("ExportUserDefinedParameterMapping", "ExportUserDefinedParameterMappingFileName")):
        if not getattr(config, flag):
            continue
        path, note = X.replacement_file(getattr(config, prop), exporter_folder)
        setattr(config, prop, path)
        if note:
            notes.append(note)
    links = config.ExportLinkedFiles
    if str(links) != "DontExport":
        config.ExportLinkedFiles = System.Enum.Parse(links.GetType(), "DontExport")
        notes.append("Setup exports linked files ({0}): changed to not exported.".format(links))
    if not config.VisibleElementsOfCurrentView:
        config.VisibleElementsOfCurrentView = True
        notes.append("Setup exports the whole model: changed to what the 3D view shows.")
    return notes


def ifc_describe(config):
    """[(item, value)] of the setup for the report."""
    out = []
    for label, prop in (("IFC version", "FileVersionDescription"), ("Site placement", "SitePlacement"),
                        ("Base quantities", "ExportBaseQuantities"),
                        ("IFC common property sets", "ExportIFCCommonPropertySets"),
                        ("Revit property sets", "ExportInternalRevitPropertySets"),
                        ("User-defined property sets", "ExportUserDefinedPsets"),
                        ("Mapping file", "ExportUserDefinedPsetsFileName"),
                        ("Store IFC GUID", "StoreIFCGUID"), ("Linked files", "ExportLinkedFiles")):
        try:
            value = getattr(config, prop)
        except Exception:
            continue
        if prop == "ExportUserDefinedPsetsFileName" and not config.ExportUserDefinedPsets:
            continue
        out.append((label, str(value)))
    return out


def export_ifc(doc, folder, file_name, view, config):
    """Export the 3D view to folder\\file_name.ifc with the setup and every linked
    item hidden. Revit needs an open transaction for IFC; it is rolled back, so the
    view and the model are not changed (also no IFC GUIDs are stored).
    Returns (path, reason, hidden, note).
    """
    from BIM.IFC.Export.UI import IFCCommandOverrideApplication
    old = IFCCommandOverrideApplication.TheDocument
    IFCCommandOverrideApplication.TheDocument = doc     # the exporter reads the model from here
    try:
        return _export_ifc(doc, folder, file_name, view, config)
    finally:
        IFCCommandOverrideApplication.TheDocument = old


def ifc_options(config, view):
    """IFCExportOptions from the setup for the view (call with TheDocument set)."""
    options = IFCExportOptions()
    config.UpdateOptions(options, view.Id)
    return options


def _export_ifc(doc, folder, file_name, view, config):
    options = ifc_options(config, view)
    items = linked_in_view(doc, view)
    hidden = [(kind, name) for _, kind, name in items]
    before = set(os.listdir(folder))
    note = ""
    ok, error = False, ""
    t = Transaction(doc, "ICSPL Export: IFC")
    t.Start()
    try:
        if items:
            try:
                view.HideElements(List[ElementId]([i for i, _, _ in items]))
                doc.Regenerate()
            except Exception as ex:
                note = "Could not hide the linked items in the view ({0}).".format(ex)
                hidden = []
        try:
            ok = doc.Export(folder, file_name + ".ifc", options)
        except Exception as ex:
            error = str(ex)
    finally:
        if t.HasStarted() and not t.HasEnded():
            t.RollBack()
    path, reason = _written(folder, before, file_name, ".ifc", ok, error)
    return path, reason, hidden, note
