# -*- coding: utf-8 -*-
"""One export run: Export window -> new dated folder -> exports -> report.

Folder layout (Akash, Step 2):
    <main folder>\\261019_ANE-\\        new every run: (2), (3) ... if it exists
        PDF\\   one PDF per sheet (drawing number + revision) + <model>_<YYMMDD>.pdf combined
        CAD\\   one DWG per sheet, same names, views merged (no xrefs), AutoCAD 2018
        <model>.nwc                     3D view picked in the window, nothing linked
        <model>.ifc                     same 3D view, setup IFC-SG, nothing linked
"""

import datetime
import os
import time

from pyrevit import forms, script

import icspl_export as X
import icspl_revit as R
import icspl_window as W

SETTING_KEYS = ("formats", "main_folder", "initials", "sheet_mode", "sheet_set", "dwg_setup",
                "pdf_setup", "nwc_view")


def run_export(uiapp, start_format):
    """Open the Export window with start_format ticked and run the export."""
    uidoc = uiapp.ActiveUIDocument
    if uidoc is None:
        forms.alert("Open a project first.", title=X.EXTENSION_NAME)
        return
    doc = uidoc.Document
    if doc.IsFamilyDocument:
        forms.alert("ICSPL Export works in a project, not in a family.", title=X.EXTENSION_NAME)
        return

    sheets = R.collect_sheets(doc)
    views = R.views_3d(doc)
    if not sheets and not views:
        forms.alert("This model has no sheets and no 3D views that can be exported.",
                    title=X.EXTENSION_NAME)
        return
    valid = set(s["id"] for s in sheets)
    model = R.model_name(doc)
    today = datetime.date.today()
    setups, active_setup = R.dwg_setups(doc)
    pdf_setups, pdf_active = R.pdf_setups(doc)
    ifc_config, ifc_folder, ifc_reason = R.ifc_setup(doc, uiapp.Application, X.IFC_SETUP)

    window = W.ExportWindow(
        sheets,
        R.browser_selected_ids(uidoc, valid),
        R.sheet_sets(doc, valid),
        X.load_settings(),
        model,
        today,
        start_format=start_format,
        owner_handle=uiapp.MainWindowHandle,
        version_text=X.revit_version_text(uiapp.Application),
        dwg_setups=setups,
        dwg_active=active_setup,
        pdf_setups=pdf_setups,
        pdf_active=pdf_active,
        nwc_views=[v["name"] for v in views],
        nwc_ok=R.nwc_available(),
        ifc_reason=ifc_reason,
    )
    choice = window.show()
    if not choice:
        return
    X.save_settings(dict((k, choice[k]) for k in SETTING_KEYS))

    main = choice["main_folder"]
    name = X.next_free_name(X.issue_folder_base(today, choice["initials"]),
                            lambda n: os.path.exists(os.path.join(main, n)))
    issue = os.path.join(main, name)
    try:
        os.makedirs(issue)
    except Exception as ex:
        forms.alert("Could not make the folder:\n{0}\n\n{1}".format(issue, ex), title=X.EXTENSION_NAME)
        return

    by_id = dict((s["id"], s) for s in sheets)
    chosen = [by_id[i] for i in choice["sheet_ids"] if i in by_id]

    output = script.get_output()
    output.set_title(X.EXTENSION_NAME)
    started = time.time()
    output.print_md(u"## ICSPL Export: {0}".format(X.md_cell(name)))
    output.print_md(u"Folder: {0}  \nModel: {1}  \n{2}".format(
        X.md_cell(issue), X.md_cell(model), X.revit_version_text(uiapp.Application)))

    if "PDF" in choice["formats"]:
        _run_pdf(doc, issue, chosen, model, today, choice.get("pdf_setup", ""), output)
    if "DWG" in choice["formats"]:
        _run_dwg(doc, issue, chosen, choice.get("dwg_setup", ""), output)
    if "NWC" in choice["formats"]:
        _run_nwc(doc, issue, model, views, choice.get("nwc_view", ""), output)
    if "IFC" in choice["formats"]:
        _run_ifc(doc, issue, model, views, choice.get("nwc_view", ""), ifc_config, ifc_folder, output)

    output.print_md(u"Finished in {0} (m:ss).".format(X.format_duration(time.time() - started)))


def _run_pdf(doc, issue, sheets, model, today, setup_name, output):
    folder = os.path.join(issue, X.PDF_FOLDER)
    os.makedirs(folder)
    files, skipped, renamed = X.plan_sheet_files(sheets)
    options, failed_options = R.pdf_options(doc, setup_name)

    written = []
    combined, combined_reason = None, ""
    total = len(files) + 1      # the last step is the combined file
    with forms.ProgressBar(title="PDF {value} of {max_value}", cancellable=True) as bar:
        for i, item in enumerate(files):
            if bar.cancelled:
                skipped.extend((f, "export cancelled") for f in files[i:])
                break
            bar.update_progress(i + 1, total)
            path, reason = R.export_pdf(doc, folder, [item["eid"]], item["file"], options)
            if path:
                written.append((item, path))
            else:
                skipped.append((item, reason))
        if bar.cancelled:
            combined_reason = "export cancelled"
        elif not written:
            combined_reason = "no single sheet PDF was written"
        else:
            bar.update_progress(total, total)
            # same options, same sheets as the single files that were written
            combined, combined_reason = R.export_pdf(
                doc, folder, [item["eid"] for item, _ in written],
                X.combined_pdf_name(model, today), options)

    output.print_md(u"### PDF: {0} written, {1} skipped".format(len(written), len(skipped)))
    output.print_md(u"Folder: {0}  \nPDF setup: {1}".format(
        X.md_cell(folder), X.md_cell(setup_name or X.PDF_DEFAULT_SETUP)))
    rows = []
    for n, (item, path) in enumerate(written, 1):
        rows.append([str(n), X.md_cell(item["number"]), X.md_cell(item["name"]),
                     X.md_cell(os.path.basename(path)), X.format_size(os.path.getsize(path))])
    if combined:
        rows.append(["", "Combined", "{0} sheets".format(len(written)),
                     X.md_cell(os.path.basename(combined)), X.format_size(os.path.getsize(combined))])
    if rows:
        output.print_table(table_data=rows, columns=["#", "Sheet Number", "Sheet Name", "File", "Size"])
    if not combined:
        output.print_md(u"**Combined PDF not made:** {0}".format(X.md_cell(combined_reason)))
    if skipped:
        output.print_table(
            table_data=[[X.md_cell(s.get("number")), X.md_cell(s.get("name")), X.md_cell(r)]
                        for s, r in skipped],
            columns=["Sheet Number", "Sheet Name", "Reason"], title="Skipped")
    _print_notes(output, renamed, failed_options, ".pdf", "PDF")


def _run_dwg(doc, issue, sheets, setup_name, output):
    folder = os.path.join(issue, X.CAD_FOLDER)
    os.makedirs(folder)
    files, skipped, renamed = X.plan_sheet_files(sheets)
    options, failed_options = R.dwg_options(doc, setup_name)

    written = []
    with forms.ProgressBar(title="DWG {value} of {max_value}", cancellable=True) as bar:
        for i, item in enumerate(files):
            if bar.cancelled:
                skipped.extend((f, "export cancelled") for f in files[i:])
                break
            bar.update_progress(i + 1, len(files))
            path, reason = R.export_dwg(doc, folder, item["eid"], item["file"], options)
            if path:
                written.append((item, path))
            else:
                skipped.append((item, reason))

    output.print_md(u"### DWG: {0} written, {1} skipped".format(len(written), len(skipped)))
    output.print_md(u"Folder: {0}  \nDWG setup: {1}".format(
        X.md_cell(folder), X.md_cell(setup_name or X.DWG_DEFAULT_SETUP)))
    rows = [[str(n), X.md_cell(item["number"]), X.md_cell(item["name"]),
             X.md_cell(os.path.basename(path)), X.format_size(os.path.getsize(path))]
            for n, (item, path) in enumerate(written, 1)]
    if rows:
        output.print_table(table_data=rows, columns=["#", "Sheet Number", "Sheet Name", "File", "Size"])
    if skipped:
        output.print_table(
            table_data=[[X.md_cell(s.get("number")), X.md_cell(s.get("name")), X.md_cell(r)]
                        for s, r in skipped],
            columns=["Sheet Number", "Sheet Name", "Reason"], title="Skipped")
    _print_notes(output, renamed, failed_options, ".dwg", "DWG")


def _run_nwc(doc, issue, model, views, view_name, output):
    file_name = X.nwc_file_name(model)
    found = [v for v in views if v["name"] == view_name]
    output.print_md(u"### NWC")
    if not found:
        output.print_md(u"**NWC not made:** 3D view {0} not found.".format(X.md_cell(view_name)))
        return
    view = doc.GetElement(found[0]["eid"])
    options, failed = R.nwc_options(view.Id)
    started = time.time()
    with forms.ProgressBar(title="NWC: exporting {0} (this can take a few minutes)".format(
            file_name), indeterminate=True):
        path, reason, hidden, note = R.export_nwc(doc, issue, file_name, view, options)
    if path:
        output.print_md(u"Written: {0}  ({1}, {2} m:ss)".format(
            X.md_cell(path), X.format_size(os.path.getsize(path)),
            X.format_duration(time.time() - started)))
    else:
        output.print_md(u"**NWC not made:** {0}".format(X.md_cell(reason)))
    output.print_md(u"3D view: {0}  \nShared coordinates, all parameters, not divided by levels, "
                    u"no rooms, no links.".format(X.md_cell(view_name)))
    if note:
        output.print_md(u"Note: {0}".format(X.md_cell(note)))
    if hidden:
        output.print_table(
            table_data=[[X.md_cell(kind), X.md_cell(name)] for kind, name in hidden],
            columns=["Left out", "Name"], title="Linked items hidden for the export")
    else:
        output.print_md(u"No linked items were visible in the view.")
    _print_notes(output, [], failed, ".nwc", "NWC")


def _run_ifc(doc, issue, model, views, view_name, config, exporter_folder, output):
    file_name = X.ifc_file_name(model)
    found = [v for v in views if v["name"] == view_name]
    output.print_md(u"### IFC")
    if not found:
        output.print_md(u"**IFC not made:** 3D view {0} not found.".format(X.md_cell(view_name)))
        return
    view = doc.GetElement(found[0]["eid"])
    notes = R.ifc_prepare(config, exporter_folder)
    started = time.time()
    with forms.ProgressBar(title="IFC: exporting {0} (this can take a few minutes)".format(
            file_name), indeterminate=True):
        path, reason, hidden, note = R.export_ifc(doc, issue, file_name, view, config)
    if path:
        output.print_md(u"Written: {0}  ({1}, {2} m:ss)".format(
            X.md_cell(path), X.format_size(os.path.getsize(path)),
            X.format_duration(time.time() - started)))
    else:
        output.print_md(u"**IFC not made:** {0}".format(X.md_cell(reason)))
    output.print_md(u"3D view: {0}  \nSetup: {1}".format(X.md_cell(view_name), X.md_cell(X.IFC_SETUP)))
    output.print_table(table_data=[[X.md_cell(a), X.md_cell(b)] for a, b in R.ifc_describe(config)],
                       columns=["Setting", "Used"], title="IFC setup")
    for text in notes + ([note] if note else []):
        output.print_md(u"Note: {0}".format(X.md_cell(text)))
    if hidden:
        output.print_table(
            table_data=[[X.md_cell(kind), X.md_cell(name)] for kind, name in hidden],
            columns=["Left out", "Name"], title="Linked items hidden for the export")
    else:
        output.print_md(u"No linked items were visible in the view.")


def _print_notes(output, renamed, failed_options, ext, label):
    if renamed:
        output.print_table(
            table_data=[[X.md_cell(s.get("number")), X.md_cell(f + ext), X.md_cell(r)]
                        for s, f, r in renamed],
            columns=["Sheet Number", "File", "Why the name differs"], title="File names changed")
    if failed_options:
        output.print_table(
            table_data=[[X.md_cell(name), X.md_cell(err)] for name, err in failed_options],
            columns=["{0} option".format(label), "Revit refused it"],
            title="{0} options not set".format(label))
