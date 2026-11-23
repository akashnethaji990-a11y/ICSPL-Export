# -*- coding: utf-8 -*-
"""Offline tests for lib/icspl_export.py (no Revit). Run: python tests\\test_icspl_export.py

Also runs in pyRevit's IronPython 2.7 engine:
    powershell -ExecutionPolicy Bypass -File tools\\ipy_run.ps1 -Py tests\\test_icspl_export.py
"""

import datetime
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "ICSPL Export.extension", "lib"))

import icspl_export as X  # noqa: E402

DAY = datetime.date(2026, 10, 19)


class Names(unittest.TestCase):
    def test_natural_sort(self):
        nums = ["S-10", "S-2", "A-1", "S-1", "S-100"]
        self.assertEqual(sorted(nums, key=X.natural_key), ["A-1", "S-1", "S-2", "S-10", "S-100"])

    def test_safe_file_name(self):
        self.assertEqual(X.safe_file_name("S-101"), ("S-101", False))
        self.assertEqual(X.safe_file_name("S/101"), ("S-101", True))
        self.assertEqual(X.safe_file_name('a\\b:c*d?e"f<g>h|i'), ("a-b-c-d-e-f-g-h-i", True))
        self.assertEqual(X.safe_file_name("S-101. "), ("S-101", True))
        self.assertEqual(X.safe_file_name("  S-1  "), ("S-1", False))

    def test_initials(self):
        self.assertEqual(X.initials_problem("ANE"), "")
        self.assertTrue(X.initials_problem(""))
        self.assertTrue(X.initials_problem("A/B"))

    def test_folder_name(self):
        self.assertEqual(X.date_stamp(DAY), "261019")
        self.assertEqual(X.issue_folder_base(DAY, " ANE "), "261019_ANE-")

    def test_next_free_name(self):
        taken = set(["261019_ANE-", "261019_ANE-(2)"])
        self.assertEqual(X.next_free_name("261019_ANE-", lambda n: n in taken), "261019_ANE-(3)")
        self.assertEqual(X.next_free_name("261020_ANE-", lambda n: n in taken), "261020_ANE-")

    def test_model_name(self):
        self.assertEqual(X.model_name_from_path(r"\\srv\P200\P200-ICSPL-BLK1.rvt"), "P200-ICSPL-BLK1")
        self.assertEqual(X.model_name_from_path("Autodesk Docs://Proj/Folder/Model A.RVT"), "Model A")
        self.assertEqual(X.model_name_from_path("Model B"), "Model B")
        self.assertEqual(X.model_name_from_path(""), "")

    def test_combined_name(self):
        self.assertEqual(X.combined_pdf_name("P200-ICSPL-BLK1-ZZ-S-STR-M3-PIM-0004", DAY),
                         "P200-ICSPL-BLK1-ZZ-S-STR-M3-PIM-0004_261019")
        self.assertEqual(X.combined_pdf_name("", DAY), "Combined_261019")


class PlanFiles(unittest.TestCase):
    def test_plan(self):
        sheets = [
            {"id": 1, "number": "S-101", "name": "A"},
            {"id": 2, "number": "S/102", "name": "B"},
            {"id": 3, "number": "", "name": "C"},
            {"id": 4, "number": "S-102", "name": "D"},      # same file name as S/102
            {"id": 5, "number": "///", "name": "E"},        # -> "---", still usable
            {"id": 6, "number": "...", "name": "F"},        # -> "", not usable
        ]
        files, skipped, renamed = X.plan_sheet_files(sheets)
        self.assertEqual([f["file"] for f in files], ["S-101", "S-102", "S-102 (2)", "---"])
        self.assertEqual([f["id"] for f in files], [1, 2, 4, 5])
        self.assertEqual([(s["id"], r) for s, r in skipped],
                         [(3, "Sheet Number is empty"),
                          (6, "Sheet Number has no characters usable in a file name")])
        self.assertEqual([(s["id"], f) for s, f, r in renamed], [(2, "S-102"), (4, "S-102 (2)"), (5, "---")])
        self.assertNotIn("file", sheets[0])                 # input not changed


class DrawingNames(unittest.TestCase):
    """Akash, 23 Nov: drawing number with / -> -, then -<revision>; '-' or empty -> one '-'."""

    def test_rule(self):
        dwg = "PRJ01/ICSPL/Z01/ZZ/S/STR/DR/DET/3791"
        self.assertEqual(X.drawing_file_name(dwg, "0.6"), "PRJ01-ICSPL-Z01-ZZ-S-STR-DR-DET-3791-0.6")
        self.assertEqual(X.drawing_file_name(dwg, "A"), "PRJ01-ICSPL-Z01-ZZ-S-STR-DR-DET-3791-A")
        self.assertEqual(X.drawing_file_name(dwg, "-"), "PRJ01-ICSPL-Z01-ZZ-S-STR-DR-DET-3791-")
        self.assertEqual(X.drawing_file_name(dwg, ""), "PRJ01-ICSPL-Z01-ZZ-S-STR-DR-DET-3791-")
        self.assertEqual(X.drawing_file_name(dwg, None), "PRJ01-ICSPL-Z01-ZZ-S-STR-DR-DET-3791-")

    def test_empty_part_kept(self):
        # sheet 3000 has no Project Location Code: exported as it is
        self.assertEqual(X.drawing_file_name("PRJ01/ICSPL//ZZ/S/STR/DR/CVS/3000", "-"),
                         "PRJ01-ICSPL--ZZ-S-STR-DR-CVS-3000-")

    def test_plan_uses_drawing_number(self):
        sheets = [
            {"id": 1, "number": "3791", "drawing_no": "PRJ01/ICSPL/Z01/ZZ/S/STR/DR/DET/3791", "revision": "0.6"},
            {"id": 2, "number": "3000", "drawing_no": "PRJ01/ICSPL//ZZ/S/STR/DR/CVS/3000", "revision": ""},
            {"id": 3, "number": "3792", "drawing_no": "PRJ01/ICSPL/Z01/ZZ/S/STR/DR/DET/37:92", "revision": "B"},
            {"id": 4, "number": "", "drawing_no": "", "revision": ""},
        ]
        files, skipped, renamed = X.plan_sheet_files(sheets)
        self.assertEqual([f["file"] for f in files], [
            "PRJ01-ICSPL-Z01-ZZ-S-STR-DR-DET-3791-0.6",
            "PRJ01-ICSPL--ZZ-S-STR-DR-CVS-3000-",
            "PRJ01-ICSPL-Z01-ZZ-S-STR-DR-DET-37-92-B",
        ])
        self.assertEqual([(s["id"], r) for s, r in skipped], [(4, "Drawing number is empty")])
        self.assertEqual([s["id"] for s, f, r in renamed], [3])   # only the ':' is reported, not the '/'


class Nwc(unittest.TestCase):
    def test_file_name(self):
        self.assertEqual(X.nwc_file_name("P200-ICSPL-BLK1-ZZ-S-STR-M3-PIM-0004-"),
                         "P200-ICSPL-BLK1-ZZ-S-STR-M3-PIM-0004-")
        self.assertEqual(X.nwc_file_name("A:B"), "A-B")
        self.assertEqual(X.nwc_file_name(""), "Model")

    def test_choose_view(self):
        names = ["3D WORKING", "IFC", "M-1", "{3D}"]
        self.assertEqual(X.choose_view(names, "IFC", "M-1"), "IFC")        # last used
        self.assertEqual(X.choose_view(names, "gone", "M-1"), "M-1")       # named like model
        self.assertEqual(X.choose_view(names, "", "other"), "3D WORKING")  # first
        self.assertEqual(X.choose_view([], "IFC", "M-1"), "")


class Ifc(unittest.TestCase):
    OLD = "C:\\Program Files\\Autodesk\\Revit 2024\\AddIns\\IFCExporterUI\\IFC-SG Property Mapping Export.txt"
    FOLDER = "C:\\ProgramData\\Autodesk\\ApplicationPlugins\\IFC 2026.bundle\\Contents\\2026"

    def test_file_name(self):
        self.assertEqual(X.ifc_file_name("P200-ICSPL-BLK1-ZZ-S-STR-M3-PIM-0004-"),
                         "P200-ICSPL-BLK1-ZZ-S-STR-M3-PIM-0004-")

    def test_replacement_file(self):
        old, folder = self.OLD, self.FOLDER
        new = os.path.join(folder, "IFC-SG Property Mapping Export.txt")
        self.assertEqual(X.replacement_file("", folder, lambda p: False), ("", ""))
        self.assertEqual(X.replacement_file(old, folder, lambda p: p == old), (old, ""))  # found: kept
        path, note = X.replacement_file(old, folder, lambda p: p == new)
        self.assertEqual(path, new)
        self.assertIn("Used:", note)
        path, note = X.replacement_file(old, folder, lambda p: False)
        self.assertEqual(path, old)
        self.assertIn("also not in", note)


class Report(unittest.TestCase):
    def test_sizes(self):
        self.assertEqual(X.format_size(512), "512 B")
        self.assertEqual(X.format_size(1536), "1.5 KB")
        self.assertEqual(X.format_size(5 * 1024 * 1024), "5.0 MB")
        self.assertEqual(X.format_duration(72.4), "1:12")

    def test_md_cell(self):
        self.assertEqual(X.md_cell("<A|B_C*D>"), "&lt;A&#124;B&#95;C&#42;D&gt;")
        self.assertEqual(X.md_cell(None), "")
        self.assertEqual(X.md_cell(3), "3")


class FakeOptions(object):
    def __init__(self):
        self.Good = None

    def __setattr__(self, name, value):
        if name not in ("Good",):
            raise AttributeError("no property " + name)
        object.__setattr__(self, name, value)


class Options(unittest.TestCase):
    def test_set_options(self):
        opts = FakeOptions()
        failed = X.set_options(opts, [("Good", 1), ("Missing", 2)])
        self.assertEqual(opts.Good, 1)
        self.assertEqual([n for n, _ in failed], ["Missing"])


class Settings(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.old = os.environ.get("APPDATA")
        os.environ["APPDATA"] = self.tmp

    def tearDown(self):
        if self.old is None:
            del os.environ["APPDATA"]
        else:
            os.environ["APPDATA"] = self.old
        shutil.rmtree(self.tmp)

    def test_merge(self):
        self.assertEqual(X.load_settings(), {})
        X.save_settings({"initials": "ANE", "formats": ["PDF"]})
        X.save_settings({"main_folder": "D:\\Issue"})
        self.assertEqual(X.load_settings(),
                         {"initials": "ANE", "formats": ["PDF"], "main_folder": "D:\\Issue"})
        self.assertTrue(X.settings_path().startswith(os.path.join(self.tmp, "ICSPLExport")))

    def test_bad_file(self):
        os.makedirs(X.settings_dir())
        with open(X.settings_path(), "w") as f:
            f.write("not json")
        self.assertEqual(X.load_settings(), {})


if __name__ == "__main__":
    # built by hand: unittest.main() needs a real __main__ module (missing in tools\ipy_run.ps1)
    cases = [v for v in list(globals().values())
             if isinstance(v, type) and issubclass(v, unittest.TestCase)]
    suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in cases])
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
