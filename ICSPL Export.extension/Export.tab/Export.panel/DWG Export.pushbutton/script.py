# -*- coding: utf-8 -*-
__title__ = "DWG Export"
__doc__ = ("Export sheets to DWG: one file per sheet (drawing number + revision), views merged, "
           "AutoCAD 2018, in a new dated folder <main folder>\\YYMMDD_<initials>-\\CAD.")

import icspl_run

icspl_run.run_export(__revit__, "DWG")
