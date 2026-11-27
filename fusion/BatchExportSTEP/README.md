# Batch STEP Export for Fusion

Batch STEP Export saves every part in a Fusion design as its own `.step` file in one click, instead of exporting them one at a time. You can export one file per component or one file per body, for the whole design or just one sub-assembly. It works in Fusion on Windows and macOS, in the Design workspace.

It's a Fusion add-in: once installed, it loads every time Fusion starts and adds a **Batch STEP Export** button to the toolbar.

## Install

Setup takes about a minute and only needs doing once.

1. Get the add-in folder onto your computer, either way works:
   - **Clone the repo** (easiest to keep up to date):
     ```sh
     git clone https://github.com/upstatecnc/cad-tools.git
     ```
   - **Or download it**: on the repo page, click **Code > Download ZIP**, unzip it, and keep the `fusion/BatchExportSTEP` folder.

   Keep the `BatchExportSTEP` folder whole. Fusion needs `BatchExportSTEP.py` and `BatchExportSTEP.manifest` side by side in a folder with the same name, plus the `resources` folder for the toolbar icon.
2. Leave the folder somewhere permanent, such as your Documents folder. Fusion loads it from there each time it starts, so don't move or delete it afterwards.
3. In Fusion, open **Utilities > Add-Ins > Scripts and Add-Ins** (or press <kbd>Shift</kbd>+<kbd>S</kbd>).
4. Click the **+** next to the list and choose **Script or add-in from device**. Select the `BatchExportSTEP` folder.
5. Find **BatchExportSTEP** in the list, check that **Run on Startup** is on, and click **Run**.

The **Batch STEP Export** button now appears on the **Utilities** tab, in the **Add-Ins** panel, and will be there every time you start Fusion.

### Updating

If you cloned the repo, run `git pull` in it. If you downloaded a ZIP, replace the folder's files with the new ones. Then restart Fusion, or in **Scripts and Add-Ins** select **BatchExportSTEP**, click **Stop**, then **Run**. Your saved options are kept.

## Export your parts

1. Open your design.
2. Click **Utilities > Add-Ins > Batch STEP Export**. A dialog opens on the right.
3. Set the options (see the table below). The line at the bottom shows how many files will be written.
4. Click **Export**. A progress bar shows each file; **Cancel** stops after the current one.
5. A summary lists how many files were saved and any that failed. The folder opens if you asked it to.

| Option | What it does |
| --- | --- |
| **Component** | Click one component in the canvas or browser to export only it and everything under it. Leave it at 0 selected to export the whole design. |
| **Export** | **One file per component:** each unique component becomes one file, even if it is used several times.<br>**One file per body:** each body becomes its own file, for designs where parts are bodies inside one component. |
| **Skip empty sub-assemblies** | Per-component mode. Skips components that only hold other components and have no bodies of their own. |
| **Skip hidden bodies** | Per-body mode. Skips bodies whose eye icon is off. |
| **Solid bodies only** | Per-body mode. Skips surface bodies. |
| **Output folder** | Where the files are saved. Type a path or click **Browse...**. **Export** stays greyed out until a real folder is set. |
| **Open folder when done** | Opens the output folder in File Explorer or Finder after exporting. |

Files are named after the component, or `Component_Body` in per-body mode. Characters that aren't allowed in file names become `_`, and duplicates within one export get `_2`, `_3` and so on. Each part keeps its own origin, not its position in the assembly.

> **Note:** files already in the output folder with the same name are overwritten without asking. Use an empty folder if you want to keep an earlier export.

Your last-used options and folder are remembered for next time.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| No button on the toolbar | Switch to the Design workspace. If it's still missing, click the arrow under **Add-Ins**, find **Batch STEP Export**, and click the pin beside it. |
| Button gone after restarting Fusion | Turn on **Run on Startup** for **BatchExportSTEP** in **Scripts and Add-Ins** (<kbd>Shift</kbd>+<kbd>S</kbd>). |
| Add-in doesn't appear in the list, or won't run | Make sure you selected the `BatchExportSTEP` folder itself (not `fusion` or the repo root), and that the `.py` and `.manifest` files are directly inside it. |
| Button shows a question mark instead of an icon | The `resources` folder is missing. Copy it back into the `BatchExportSTEP` folder. |
| **Export** is greyed out | Set an output folder that exists. |
| Count shows 0 files | Untick the skip options, or check that the selected component has bodies. |
| A part is listed as failed | Re-export that part on its own with **File > Export** to see Fusion's error. Broken or empty bodies are the usual cause. |

Exporting leaves your design unchanged. Per-body mode briefly adds a temporary component for each body and removes it again straight away.

## Safety and privacy

The add-in works only on your computer and never connects to the internet. The code is plain, readable Python, so you can open [`BatchExportSTEP.py`](BatchExportSTEP.py) in any text editor and check it yourself. It only:

- writes `.step` files into the folder you choose
- saves your last-used options to `settings.json` in your user settings folder (`%APPDATA%\BatchExportSTEP` on Windows, `~/Library/Application Support/BatchExportSTEP` on Mac)
- opens the output folder when the export finishes, if that option is ticked

It never reads anything outside the open design and its own settings file, and never deletes files. The only files it changes are `.step` files it overwrites in the output folder (see the note above).

## Uninstall

In **Scripts and Add-Ins** (<kbd>Shift</kbd>+<kbd>S</kbd>), select **BatchExportSTEP**, click **Stop**, then remove it from the list. Delete the `BatchExportSTEP` folder (or the whole cloned repo if you don't need the other tools). To remove saved options too, delete the `BatchExportSTEP` settings folder listed under [Safety and privacy](#safety-and-privacy).
