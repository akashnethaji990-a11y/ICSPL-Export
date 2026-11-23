# -*- coding: utf-8 -*-
__title__ = "NWC Export"
__doc__ = ("Export a 3D view to Navisworks NWC: <model>.nwc in a new dated folder "
           "<main folder>\YYMMDD_<initials>-, shared coordinates, all parameters, nothing linked.")

import icspl_run

icspl_run.run_export(__revit__, "NWC")
