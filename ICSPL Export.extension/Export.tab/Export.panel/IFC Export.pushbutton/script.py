# -*- coding: utf-8 -*-
__title__ = "IFC Export"
__doc__ = ("Export a 3D view to IFC with the setup IFC-SG Regulatory Requirements View: "
           "<model>.ifc in a new dated folder <main folder>\\YYMMDD_<initials>-, nothing linked.")

import icspl_run

icspl_run.run_export(__revit__, "IFC")
