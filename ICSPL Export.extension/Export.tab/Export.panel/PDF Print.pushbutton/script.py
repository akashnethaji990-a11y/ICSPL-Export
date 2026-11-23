# -*- coding: utf-8 -*-
__title__ = "PDF Print"
__doc__ = ("Export sheets to PDF: one file per sheet (Sheet Number) plus one combined file, "
           "in a new dated folder <main folder>\\YYMMDD_<initials>-\\PDF.")

import icspl_run

icspl_run.run_export(__revit__, "PDF")
