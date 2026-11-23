# -*- coding: utf-8 -*-
"""Static checks in pyRevit's IronPython 2.7 engine (no Revit running):

    powershell -ExecutionPolicy Bypass -File tools\\ipy_run.ps1 -Py tests\\ipy_syntax.py

1. every .py in the extension compiles as IronPython 2.7 and is ASCII;
2. lib/icspl_revit.py imports against the Revit 2024 RevitAPI.dll, and every
   PDF / DWG / NWC option it sets is a property of the options class.
"""

import os
import sys

import clr

HERE = os.path.dirname(os.path.abspath(__file__))
EXT = os.path.join(os.path.dirname(HERE), "ICSPL Export.extension")
REVIT_API = r"C:\Program Files\Autodesk\Revit 2024\RevitAPI.dll"

failures = []


def check(cond, text):
    print("  {0}  {1}".format("ok  " if cond else "FAIL", text))
    if not cond:
        failures.append(text)


print("1. Compile + ASCII")
for folder, _, names in os.walk(EXT):
    for name in sorted(names):
        if not name.endswith(".py"):
            continue
        path = os.path.join(folder, name)
        rel = os.path.relpath(path, EXT)
        with open(path, "rb") as f:
            data = f.read()
        try:
            data.decode("ascii")
            ascii_ok = True
        except UnicodeDecodeError:
            ascii_ok = False
        check(ascii_ok, "ASCII  " + rel)
        try:
            compile(data.replace("\r\n", "\n"), path, "exec")
            check(True, "compiles  " + rel)
        except SyntaxError as ex:
            check(False, "compiles  {0}: {1}".format(rel, ex))

print("2. Revit API names (Revit 2024 DLL)")
if os.path.isfile(REVIT_API):
    clr.AddReferenceToFileAndPath(REVIT_API)
    import icspl_revit as R
    from Autodesk.Revit.DB import PDFExportOptions
    props = set(p.Name for p in clr.GetClrType(PDFExportOptions).GetProperties())
    for name, value in R.pdf_option_values():
        check(name in props, "PDFExportOptions.{0} = {1}".format(name, value))
    for name in ("Combine", "FileName"):
        check(name in props, "PDFExportOptions.{0}".format(name))
    from Autodesk.Revit.DB import DWGExportOptions
    props = set(p.Name for p in clr.GetClrType(DWGExportOptions).GetProperties())
    for name, value in R.dwg_option_values():
        check(name in props, "DWGExportOptions.{0} = {1}".format(name, value))
    from Autodesk.Revit.DB import NavisworksExportOptions, ElementId
    props = set(p.Name for p in clr.GetClrType(NavisworksExportOptions).GetProperties())
    for name, value in R.nwc_option_values(ElementId(1)):
        check(name in props, "NavisworksExportOptions.{0} = {1}".format(name, value))
    from Autodesk.Revit.DB import IFCExportOptions
    check(R.IFCExportOptions is IFCExportOptions, "IFCExportOptions imported")
    check(callable(R.ifc_setup) and callable(R.export_ifc), "IFC helpers load without the IFC add-in")
else:
    print("  skipped: {0} not found".format(REVIT_API))

print("")
print("{0} failure(s)".format(len(failures)))
sys.exit(1 if failures else 0)
