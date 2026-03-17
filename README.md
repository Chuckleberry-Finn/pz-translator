## pz-translator <sup><sub><sup><sub>3.0</sup></sub></sup></sub>
### Automated batch-capable Project Zomboid B42 translations.
#### <sup>[original concept](https://github.com/Poltergeist-PZ-Modding/pz-translator) by Poltergeist</sup>
#### <sup>PZ Translation .txt to .json converter script - MassCraxx, tweaked by SimKDT</sup>
#### <sup>[PZ-Wiki Translation](https://pzwiki.net/wiki/Translation)</sup>
#### <sup>[Translation Data](https://github.com/SirDoggyJvla/pz-translation-data) by SimKDT</sup>
<br/>

## How to Use (Simple)
- Run the `pzTranslate.exe` (utilizes PyInstaller built PyQt GUI)
- Select any directory to process.
  - Any `Translate` subdirectories will be processed.
  - Note: Google Translator has a 200k character daily limit.
- Select which Languages you would like files to be generated for.
  - Note: Selecting no languages will enable all languages.
- Optionally enable **Overwrite** to re-translate keys that already exist in target files.
  - By default, existing translated keys are preserved and only missing ones are filled in.
<br/>

## B42 Behaviour

The tool targets B42 `Translate` directories and always outputs `.json` files. Both `.json` and old-format `.txt` source files are supported as input.

| Source files | Output |
|-------------|--------|
| `.json`     | `.json` (UTF-8) |
| `.txt` (pre-42.15 format) | `.json` (UTF-8) — converted automatically |

Old pre-42.15 `.txt` translation files are parsed and written out as properly formatted B42.15 `.json` files as a natural part of the translation process.
<br/>
<br/>

### Developed Using
#### Note: You can also download these programs if you wish to modify any stage of the translation process.
| Dependency                                                                                     |  Purpose                                                     |
|------------------------------------------------------------------------------------------------|--------------------------------------------------------------|
| [**Python**](https://www.python.org/downloads/) <sup><sub>3.10+</sup></sub>                    | Runs the translation and GUI scripts.                        |
| [**deep_translator**](https://pypi.org/project/deep-translator/) <sup><sub>1.11.4+</sup></sub> | Handles automated language translation via Google Translate. |
| [**PyQt5**](https://pypi.org/project/PyQt5/) <sup><sub>5.15.11+</sup></sub>                    | Provides the graphical user interface (GUI).                 |
| [**PyInstaller**](https://pypi.org/project/pyinstaller/) <sup><sub>6.11.1+</sup></sub>         | Packages the Python script into a standalone executable.     |
<br/>

## How to Use (Complex)

In any CLI (cmd), run `repository/pz-translator/translate.py` with any relative path to any directory you want processed.

**Parameters:**

| Parameter | Description |
|-----------|-------------|
| `<directory>` | Root directory to process (required) |
| `-source <code>` | Source language code (default: `EN`) |
| `-languages <codes>` | Space-separated language codes to translate to (default: all) |
| `-overwrite` | Re-translate keys that already exist in target files |

**Example Parameters:**

For a singular sub-mod within a mods folder:
```
py translate.py "\Workshop\<your mod>\Contents\mods\<your mod>\"
```
For a mod along with any sub-mods:
```
py translate.py "\Workshop\<your mod>\"
```
For all mods, specific languages only:
```
py translate.py "\Workshop\" -languages DE FR RU
```
For all mods, overwriting all existing translations:
```
py translate.py "\Workshop\" -overwrite
```

- The script will parse through every subdirectory to find any `\Translate` directories.
- If you install PyQt5 you can also run `TranslateGUI.py` directly.
<br/>

### IntelliJ
Go to the `translate.py` file and select to `edit configurations`.
> ![image](https://github.com/user-attachments/assets/371e67be-9af6-4a9a-9642-06c18ed054c4)

Once in the configurations menu, enter in a relative path you want processed as the parameter.

> ![image](https://github.com/user-attachments/assets/af78d733-1208-4619-9c39-d33c2f15c9fb)

<br/>

### Command Line
Example for Windows — you can also write this into a `.cmd` file for a shortcut.
```
py "repository/pz-translator/translate.py" "relative-path to translate"
```
<br/>

### VSCode Task

You can add a task like this to run the script. This will target the workspaceFolder for translation.
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Translate Project",
      "type": "shell",
      "command": "py",
      "args": [ "repository/pz-translator/translate.py", "${workspaceFolder}" ],
      "group": "none",
      "presentation": {
        "reveal": "always",
        "panel": "new"
      }
    }
  ]
}
```
> <sup>See https://go.microsoft.com/fwlink/?LinkId=733558 for the documentation about the tasks.json format</sup>
<br/>

## Text Translator

Deep translator supports different translation backends. More information at: [https://pypi.org/project/deep-translator/](https://pypi.org/project/deep-translator/)
<br/>

### *WARNING: By default the script skips keys that already exist in target files. Use `-overwrite` to replace them. If you are not using version control, keep backups!*
