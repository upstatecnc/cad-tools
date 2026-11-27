"""
BatchExportSTEP - Fusion add-in

Adds a "Batch STEP Export" button to Utilities > Add-Ins in the Design workspace.
The button opens a command dialog where you set everything before exporting:
  - Scope: select one component in the canvas/browser, or leave empty for the whole design
  - Export: one STEP file per component, or one per body
  - Options: skip empty sub-assemblies / skip hidden bodies / solid bodies only
  - Output folder (with Browse button) and "open folder when done"
  - Live count of how many files will be written

Your last-used options and folder are remembered in a settings.json file in your
user app-data folder (see settings_path), so they survive updates to the add-in.
"""

import adsk.core
import adsk.fusion
import traceback
import os
import re
import sys
import json
import subprocess

ADDIN_NAME = 'BatchExportSTEP'
CMD_ID = 'BatchExportSTEP_cmd'
CMD_NAME = 'Batch STEP Export'
CMD_TIP = 'Export each component or body to its own STEP file'
WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidScriptsAddinsPanel'
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')

DEFAULTS = {
    'mode': 0,              # 0 = per component, 1 = per body
    'skip_empty': True,
    'skip_hidden': False,
    'solids_only': True,
    'folder': '',
    'open_folder': True,
}

_app = None
_ui = None
_handlers = []       # lives for the whole session (button click handler)
_cmd_handlers = []   # lives for one open dialog; replaced each time it opens


# ---------------- helpers ----------------

def settings_path():
    if sys.platform.startswith('win'):
        base = os.environ.get('APPDATA') or os.path.expanduser('~\\AppData\\Roaming')
    elif sys.platform == 'darwin':
        base = os.path.expanduser('~/Library/Application Support')
    else:
        base = os.path.expanduser('~/.config')
    return os.path.join(base, ADDIN_NAME, 'settings.json')


def load_settings():
    s = dict(DEFAULTS)
    try:
        with open(settings_path(), 'r') as f:
            s.update(json.load(f))
    except Exception:
        pass
    return s


def save_settings(s):
    try:
        path = settings_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(s, f, indent=2)
    except Exception:
        pass  # not critical


def sanitize(name):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip().rstrip('.')
    return name or 'unnamed'


def unique_path(folder, base, used):
    name = base
    i = 2
    while name.lower() in used:
        name = f'{base}_{i}'
        i += 1
    used.add(name.lower())
    return os.path.join(folder, name + '.step')


def collect_components(scope_comp):
    comps = {scope_comp.id: scope_comp}
    for occ in scope_comp.allOccurrences:
        c = occ.component
        if c.id not in comps:
            comps[c.id] = c
    return list(comps.values())


def build_jobs(scope_comp, s):
    """Returns a list of (label, component, body-or-None)."""
    jobs = []
    per_body = s['mode'] == 1
    for c in collect_components(scope_comp):
        if per_body:
            for b in c.bRepBodies:
                if s['solids_only'] and not b.isSolid:
                    continue
                if s['skip_hidden'] and not b.isLightBulbOn:
                    continue
                jobs.append((f'{c.name}_{b.name}', c, b))
        else:
            if s['skip_empty'] and c.bRepBodies.count == 0:
                continue
            jobs.append((c.name, c, None))
    return jobs


def get_scope(inputs):
    design = adsk.fusion.Design.cast(_app.activeProduct)
    sel = adsk.core.SelectionCommandInput.cast(inputs.itemById('scope'))
    if sel and sel.selectionCount > 0:
        occ = adsk.fusion.Occurrence.cast(sel.selection(0).entity)
        if occ:
            return occ.component
    return design.rootComponent


def read_inputs(inputs):
    dd = adsk.core.DropDownCommandInput.cast(inputs.itemById('mode'))
    return {
        'mode': dd.selectedItem.index if dd.selectedItem else 0,
        'skip_empty': inputs.itemById('skip_empty').value,
        'skip_hidden': inputs.itemById('skip_hidden').value,
        'solids_only': inputs.itemById('solids_only').value,
        'folder': inputs.itemById('folder').value.strip(),
        'open_folder': inputs.itemById('open_folder').value,
    }


def update_ui(inputs):
    s = read_inputs(inputs)
    per_body = s['mode'] == 1
    inputs.itemById('skip_empty').isVisible = not per_body
    inputs.itemById('skip_hidden').isVisible = per_body
    inputs.itemById('solids_only').isVisible = per_body

    scope = get_scope(inputs)
    count = len(build_jobs(scope, s))
    inputs.itemById('summary').formattedText = (
        f'<b>{count}</b> STEP file(s) from "{scope.name}"')


def open_folder(folder):
    try:
        if sys.platform.startswith('win'):
            os.startfile(folder)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', folder])
    except Exception:
        pass


def do_export(scope_comp, s):
    design = adsk.fusion.Design.cast(_app.activeProduct)
    root = design.rootComponent
    export_mgr = design.exportManager
    folder = s['folder']

    jobs = build_jobs(scope_comp, s)
    if not jobs:
        _ui.messageBox('Nothing to export with these settings.')
        return

    used = set()
    exported, failed = 0, []

    prog = _ui.createProgressDialog()
    prog.isCancelButtonShown = True
    prog.show(CMD_NAME, 'Exporting %v of %m', 0, len(jobs))

    for i, (label, comp, body) in enumerate(jobs):
        if prog.wasCancelled:
            break
        prog.progressValue = i
        adsk.doEvents()

        path = unique_path(folder, sanitize(label), used)
        temp_occ = None
        try:
            if body is None:
                target = comp
            else:
                # Bodies can't be exported directly: copy into a temp component, export, delete.
                temp_occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
                temp_occ.component.name = sanitize(label)
                body.copyToComponent(temp_occ)
                target = temp_occ.component

            opts = export_mgr.createSTEPExportOptions(path, target)
            if export_mgr.execute(opts):
                exported += 1
            else:
                failed.append(label)
        except Exception:
            failed.append(label)
        finally:
            if temp_occ and temp_occ.isValid:
                temp_occ.deleteMe()

    prog.hide()

    msg = f'Exported {exported} STEP file(s) to:\n{folder}'
    if failed:
        shown = '\n'.join(failed[:20])
        more = f'\n...and {len(failed) - 20} more' if len(failed) > 20 else ''
        msg += f'\n\nFailed ({len(failed)}):\n{shown}{more}'
    _ui.messageBox(msg, CMD_NAME)

    if s['open_folder'] and exported:
        open_folder(folder)


# ---------------- event handlers ----------------

class CreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        try:
            cmd = adsk.core.Command.cast(args.command)
            if not adsk.fusion.Design.cast(_app.activeProduct):
                _ui.messageBox('Open a design in the Design workspace first.', CMD_NAME)
                return

            cmd.okButtonText = 'Export'
            cmd.setDialogMinimumSize(380, 300)
            inputs = cmd.commandInputs
            s = load_settings()

            sel = inputs.addSelectionInput('scope', 'Component',
                                           'Select one component, or leave empty for the whole design')
            sel.addSelectionFilter('Occurrences')
            sel.setSelectionLimits(0, 1)

            dd = inputs.addDropDownCommandInput('mode', 'Export',
                                                adsk.core.DropDownStyles.TextListDropDownStyle)
            dd.listItems.add('One file per component', s['mode'] == 0)
            dd.listItems.add('One file per body', s['mode'] == 1)

            inputs.addBoolValueInput('skip_empty', 'Skip empty sub-assemblies', True, '', s['skip_empty'])
            inputs.addBoolValueInput('skip_hidden', 'Skip hidden bodies', True, '', s['skip_hidden'])
            inputs.addBoolValueInput('solids_only', 'Solid bodies only', True, '', s['solids_only'])

            inputs.addStringValueInput('folder', 'Output folder', s['folder'])
            browse = inputs.addBoolValueInput('browse', ' ', False, '', False)
            browse.text = 'Browse...'

            inputs.addBoolValueInput('open_folder', 'Open folder when done', True, '', s['open_folder'])

            inputs.addTextBoxCommandInput('summary', '', '', 1, True)

            _cmd_handlers.clear()
            for event, handler in (
                    (cmd.inputChanged, InputChangedHandler()),
                    (cmd.validateInputs, ValidateHandler()),
                    (cmd.activate, ActivateHandler()),
                    (cmd.execute, ExecuteHandler())):
                event.add(handler)
                _cmd_handlers.append(handler)
        except Exception:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class ActivateHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        try:
            update_ui(args.command.commandInputs)
        except Exception:
            pass


class InputChangedHandler(adsk.core.InputChangedEventHandler):
    def notify(self, args):
        try:
            inputs = args.inputs
            if args.input.id == 'browse':
                dlg = _ui.createFolderDialog()
                dlg.title = 'Choose a folder for the STEP files'
                current = inputs.itemById('folder').value
                if os.path.isdir(current):
                    dlg.initialDirectory = current
                if dlg.showDialog() == adsk.core.DialogResults.DialogOK:
                    inputs.itemById('folder').value = dlg.folder
            if args.input.id != 'summary':
                update_ui(inputs)
        except Exception:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class ValidateHandler(adsk.core.ValidateInputsEventHandler):
    def notify(self, args):
        try:
            folder = args.inputs.itemById('folder').value.strip()
            args.areInputsValid = bool(folder) and os.path.isdir(folder)
        except Exception:
            args.areInputsValid = False


class ExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        try:
            inputs = args.command.commandInputs
            s = read_inputs(inputs)
            save_settings(s)
            do_export(get_scope(inputs), s)
        except Exception:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


# ---------------- add-in entry points ----------------

def remove_ui():
    panel = _ui.allToolbarPanels.itemById(PANEL_ID)
    control = panel.controls.itemById(CMD_ID) if panel else None
    if control:
        control.deleteMe()
    cmd_def = _ui.commandDefinitions.itemById(CMD_ID)
    if cmd_def:
        cmd_def.deleteMe()


def run(context):
    global _app, _ui
    try:
        _app = adsk.core.Application.get()
        _ui = _app.userInterface

        remove_ui()  # clear leftovers if a previous session didn't stop cleanly

        cmd_def = _ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_TIP, ICON_FOLDER)
        on_created = CreatedHandler()
        cmd_def.commandCreated.add(on_created)
        _handlers.append(on_created)

        panel = _ui.workspaces.itemById(WORKSPACE_ID).toolbarPanels.itemById(PANEL_ID)
        control = panel.controls.addCommand(cmd_def)
        control.isPromotedByDefault = True
        control.isPromoted = True
    except Exception:
        if _ui:
            _ui.messageBox('Failed to start {}:\n{}'.format(CMD_NAME, traceback.format_exc()))


def stop(context):
    try:
        if _ui:
            remove_ui()
    except Exception:
        pass
    _handlers.clear()
    _cmd_handlers.clear()
