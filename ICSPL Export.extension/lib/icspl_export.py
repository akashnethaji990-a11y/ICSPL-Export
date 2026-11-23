# -*- coding: utf-8 -*-
"""Shared helpers for the ICSPL Export extension (IronPython 2.7).

One code base for Revit 2024, 2025 and 2026. Anything whose API differs
between those versions goes through a helper in this file.
Nothing here imports the Revit API, so it also runs in CPython (tests).
"""

import json
import os
import re

EXTENSION_NAME = "ICSPL Export"
SETTINGS_FOLDER_NAME = "ICSPLExport"
SETTINGS_FILE_NAME = "settings.json"
SUPPORTED_REVIT_YEARS = (2024, 2025, 2026)

# Formats in the Export window, in ribbon order. BUILT_FORMATS can be ticked.
FORMATS = ("PDF", "DWG", "NWC", "IFC")
BUILT_FORMATS = ("PDF", "DWG", "NWC", "IFC")

# Shown in the window for the "DWG setup" choice when the model has none.
DWG_DEFAULT_SETUP = "<Revit default>"

DWG_SUMMARY = (
    "DWG: one file per sheet (same names as the PDFs) in CAD, views merged into the "
    "sheet (no xref files), AutoCAD 2018, layers/colours from the DWG setup above."
)

NWC_SUMMARY = (
    "NWC: {0} in the new folder (no subfolder), what the 3D view above shows, shared "
    "coordinates, all parameters, not divided by levels, no rooms. Nothing linked: no "
    "Revit/IFC links, no CAD, PDF, images or point clouds (hidden for the export only)."
)
NWC_MISSING = "NWC (exporter not installed for {0})"

# IFC: always this setup (Akash, 23 Nov). Revit's built-in IFC-SG setup plus the
# changes saved in the model, read by Revit's own IFC exporter.
IFC_SETUP = "IFC-SG Regulatory Requirements View"
IFC_SUMMARY = (
    "IFC: {0} in the new folder (no subfolder), setup " + IFC_SETUP + ", what the 3D view "
    "above shows. Nothing linked (hidden for the export only)."
)
IFC_MISSING = "IFC (not available: {0})"

# Sheet sources in the Export window.
SHEET_MODES = ("pick", "browser", "set")

PDF_FOLDER = "PDF"
CAD_FOLDER = "CAD"

PDF_SUMMARY = (
    "PDF: one file per sheet, named by drawing number + revision, plus one combined file "
    "({0}) with the same settings. {1}"
)
PDF_SETUP_NOTE = (
    "Settings from the PDF setup above (its file name rule is not used). Always hidden: "
    "ref/work planes, scope boxes, crop boundaries, unreferenced view tags."
)
PDF_DEFAULT_NOTE = (
    "Colour, sheet size, vector, raster High, zoom 100%. Hidden: ref/work planes, "
    "scope boxes, crop boundaries, unreferenced view tags."
)
# Shown in the window for the "PDF setup" choice when the model has none.
PDF_DEFAULT_SETUP = "<ICSPL default>"

# Characters Windows does not allow in file and folder names.
BAD_NAME_CHARS = '\\/:*?"<>|'


def revit_year(application):
    """Revit year as an int, e.g. 2026."""
    return int(application.VersionNumber)


def revit_version_text(application):
    """Short label such as 'Revit 2026' for the running Revit."""
    return "Revit {0}".format(application.VersionNumber)


def is_supported_revit(application):
    """True when the running Revit is one of SUPPORTED_REVIT_YEARS."""
    return revit_year(application) in SUPPORTED_REVIT_YEARS


def element_id_value(element_id):
    """Numeric id of an ElementId.

    Revit 2024 and later expose ElementId.Value (Int64). Older versions only
    have IntegerValue, so fall back to that if Value is missing.
    """
    try:
        return element_id.Value
    except AttributeError:
        return element_id.IntegerValue


def coming_soon_message(button_name, application):
    """Message shown by the placeholder buttons."""
    text = "{0}: coming soon\n\n{1}".format(button_name, revit_version_text(application))
    if not is_supported_revit(application):
        text += "\n\nWarning: this extension is built for Revit 2024-2026."
    return text


def set_options(options, values):
    """Set export option properties one by one.

    values: list of (property name, value), set in that order.
    Returns [(name, error text)] for the ones Revit refused, so a property
    that differs between Revit versions is reported instead of stopping
    the export.
    """
    failed = []
    for name, value in values:
        try:
            setattr(options, name, value)
        except Exception as ex:
            failed.append((name, str(ex)))
    return failed


# ---------------------------------------------------------------- names

def natural_key(text):
    """Sort key that puts S-2 before S-10."""
    parts = re.split(r"(\d+)", text or "")
    return [(0, int(p), "") if p.isdigit() else (1, 0, p.lower()) for p in parts]


def safe_file_name(text):
    """(name, changed): text with characters Windows refuses replaced by '-'.

    Trailing dots and spaces are removed too (Windows drops them).
    """
    original = (text or "").strip()
    out = []
    for ch in original:
        if ch in BAD_NAME_CHARS or ord(ch) < 32:
            out.append("-")
        else:
            out.append(ch)
    name = "".join(out).rstrip(". ")
    return name, name != original


def initials_problem(text):
    """Why the initials can't be used in a folder name, or '' if they can."""
    text = (text or "").strip()
    if not text:
        return "Enter your initials."
    name, changed = safe_file_name(text)
    if changed or not name:
        return "Initials: no \\ / : * ? \" < > | allowed."
    return ""


def date_stamp(day):
    """YYMMDD, e.g. 261019 for 19 Oct 2026."""
    return day.strftime("%y%m%d")


def issue_folder_base(day, initials):
    """Main export folder name: 261019_ANE-"""
    return "{0}_{1}-".format(date_stamp(day), initials.strip())


def next_free_name(base, exists):
    """base, or base(2), base(3) ... : the first name for which exists() is False."""
    if not exists(base):
        return base
    n = 2
    while exists("{0}({1})".format(base, n)):
        n += 1
    return "{0}({1})".format(base, n)


def model_name_from_path(path):
    """Model file name without folder and without .rvt (works for / and \\)."""
    name = re.split(r"[\\/]", (path or "").strip())[-1]
    if name.lower().endswith(".rvt"):
        name = name[:-4]
    return name.strip()


def combined_pdf_name(model_name, day):
    """Combined PDF file name without .pdf: <model>_<YYMMDD>."""
    name, _ = safe_file_name("{0}_{1}".format(model_name or "Combined", date_stamp(day)))
    return name


def nwc_file_name(model_name):
    """NWC file name without .nwc: the model name (Akash, 23 Nov)."""
    name, _ = safe_file_name(model_name or "Model")
    return name or "Model"


def ifc_file_name(model_name):
    """IFC file name without .ifc: the model name (Akash, 23 Nov)."""
    return nwc_file_name(model_name)


def replacement_file(path, folder, exists=os.path.isfile):
    """(path to use, note) for a mapping file named in an IFC setup.

    The IFC-SG setup in the model points to the Revit 2024 Program Files folder,
    where the file is missing (Akash, 23 Nov: use the running Revit's file).
    path empty or found -> (path, ""). Else the same file name in folder (the IFC
    exporter add-in of the running Revit) -> (that path, note). Else (path, warning).
    """
    path = (path or "").strip()
    if not path or exists(path):
        return path, ""
    alt = os.path.join(folder or "", re.split(r"[\\/]", path)[-1])
    if folder and exists(alt):
        return alt, "Mapping file not found: {0}. Used: {1}".format(path, alt)
    return path, "Mapping file not found: {0} (also not in {1})".format(path, folder or "-")


def choose_view(names, last, model_name):
    """3D view to pre-select for NWC: last used, else the one named like the model,
    else the first. "" if there are none."""
    names = list(names or [])
    for wanted in (last, model_name):
        if wanted and wanted in names:
            return wanted
    return names[0] if names else ""


def drawing_file_name(drawing_no, revision):
    """File name (no extension) from the drawing number and the revision (Akash, 23 Nov).

    PRJ01/ICSPL/Z01/ZZ/S/STR/DR/DET/3791 + 0.6 -> PRJ01-ICSPL-Z01-ZZ-S-STR-DR-DET-3791-0.6
    Revision "-" or empty -> one "-" at the end. An empty part stays as "--" (not edited).
    """
    drawing_no = (drawing_no or "").strip()
    revision = (revision or "").strip()
    name = drawing_no + ("-" if revision in ("", "-") else "-" + revision)
    return name.replace("/", "-")


def plan_sheet_files(sheets):
    """File name (without extension) for each sheet.

    sheets: dicts with "number", and "drawing_no" + "revision" when known
    (then the name is drawing_file_name(); else the Sheet Number).
    Returns (files, skipped, renamed):
      files   - copies of the sheet dicts with "file" added
      skipped - [(sheet, reason)]
      renamed - [(sheet, file, reason)] when a character had to be replaced
                ("/" -> "-" in a drawing number is the rule, not reported)
    """
    files, skipped, renamed = [], [], []
    used = set()
    for sheet in sheets:
        if "drawing_no" in sheet:
            source = drawing_file_name(sheet.get("drawing_no"), sheet.get("revision"))
            what = "Drawing number"
        else:
            source = (sheet.get("number") or "").strip()
            what = "Sheet Number"
        if not source.strip("-"):
            skipped.append((sheet, "{0} is empty".format(what)))
            continue
        clean, changed = safe_file_name(source)
        if not clean:
            skipped.append((sheet, "{0} has no characters usable in a file name".format(what)))
            continue
        name, n = clean, 2
        while name.lower() in used:
            name = "{0} ({1})".format(clean, n)
            n += 1
        used.add(name.lower())
        if name != clean:
            renamed.append((sheet, name, "same file name as another sheet"))
        elif changed:
            renamed.append((sheet, name, "character not allowed in file names"))
        item = dict(sheet)
        item["file"] = name
        files.append(item)
    return files, skipped, renamed


# ---------------------------------------------------------------- report

def format_size(num_bytes):
    """1.2 MB style size."""
    size = float(num_bytes or 0)
    for unit in ("B", "KB", "MB"):
        if size < 1024.0:
            return "{0:.0f} {1}".format(size, unit) if unit == "B" else "{0:.1f} {1}".format(size, unit)
        size /= 1024.0
    return "{0:.1f} GB".format(size)


def format_duration(seconds):
    """m:ss"""
    seconds = int(round(seconds or 0))
    return "{0}:{1:02d}".format(seconds // 60, seconds % 60)


def md_cell(text):
    """Text safe for pyRevit markdown (pyRevit hides <...>; _ and * would make italics)."""
    text = u"{0}".format(text if text is not None else "")
    for old, new in (("&", "&amp;"), ("<", "&lt;"), (">", "&gt;"), ("|", "&#124;"),
                     ("_", "&#95;"), ("*", "&#42;"), ("\\", "&#92;")):
        text = text.replace(old, new)
    return text


# ---------------------------------------------------------------- settings

def settings_dir():
    """Folder for settings.json: %APPDATA%\\ICSPLExport."""
    return os.path.join(os.environ.get("APPDATA", ""), SETTINGS_FOLDER_NAME)


def settings_path():
    return os.path.join(settings_dir(), SETTINGS_FILE_NAME)


def load_settings():
    """Saved settings as a dict ({} if missing or unreadable)."""
    try:
        with open(settings_path(), "r") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_settings(updates):
    """Merge updates into settings.json (other keys are kept)."""
    data = load_settings()
    data.update(updates)
    folder = settings_dir()
    if not os.path.isdir(folder):
        os.makedirs(folder)
    with open(settings_path(), "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    return data
