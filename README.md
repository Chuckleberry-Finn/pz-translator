## pz-translator <sup><sub><sup><sub>2.0</sup></sub></sup></sub>
### Automated batch-capable Project Zomboid translations.
#### <sup>[original concept](https://github.com/Poltergeist-PZ-Modding/pz-translator) by [Poltergeist](https://github.com/Poltergeist-ix).</sup>  
<br/>

## How to use
- Run the `pzTranslate.exe` (utilizes PyInstaller built PyQt GUI)
- Select any directory to process.
  - Any `Translate` subdirectories will be processed.
  - Note: Google Translator has a 200k character daily limit.
- Select if you would like B41 directories to be processed.
- Select which Languages you would like files to be generated for.
  - Note: Selecting no languages will enabled all languages.
<br/>
<br/>

### Developed Using
#### Note: You can also download these programs if you wish to modify any stage of the translation process.
| Dependency                                                                                     | Purpose |
|------------------------------------------------------------------------------------------------|---------|
| [**Python**](https://www.python.org/downloads/) <sup><sub>3.10+</sup></sub>                    | Runs the translation and GUI scripts. |
| [**deep_translator**](https://pypi.org/project/deep-translator/) <sup><sub>1.11.4+</sup></sub> | Handles automated language translation via Google Translate. |
| [**PyQt5**](https://pypi.org/project/PyQt5/) <sup><sub>5.15.11+</sup></sub>                    | Provides the graphical user interface (GUI). |
| [**PyInstaller**](https://pypi.org/project/pyinstaller/) <sup><sub>6.11.1+</sup></sub>         | Packages the Python script into a standalone executable.
<br/>

## How to use

Run the `pzTranslate.exe` which is a PyQt

run `repository/pz-translator/translate.py` with any relative path to any directory you want processed as a parameter, additionally skip over B41 directories using `-no41`

**Example Parameters:**

For a singular sub-mod with-in a mods folder:
```
\Workshop\<your mod>\Contents\mods\<your mod>\ -no41
```
For a mod along with any sub-mods:
```
\Workshop\<your mod>\ -no41
```
For all mods:
```
\Workshop\ -no41
```

- The script will parse through every subdirectory to find any `\Translate` directories.
- Note: Depending on the position relative to a \mods\ folder, the script will utilize  encodings for either B41 or B42.  
<br/>

### IntelliJ
Go to the `translate.py` file and select to `edit configurations`.
> ![image](https://github.com/user-attachments/assets/371e67be-9af6-4a9a-9642-06c18ed054c4)

Once in the configurations menu, enter in a relative path you want processed as the parameter.

> ![image](https://github.com/user-attachments/assets/9e0a0cbf-4aa6-49f6-bd3c-7f35745960a1)  
<br/>

### Command Line
example for windows, you can also write this into a cmd file for shortcut.
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
    },
  ]
}

```
> <sup>See https://go.microsoft.com/fwlink/?LinkId=733558 for the documentation about the tasks.json format</sup>  
<br/>

## Text Translator

Deep translator supports different translators, you can find more information at: [https://pypi.org/project/deep-translator/](https://pypi.org/project/deep-translator/)  
<br/>

### *WARINIG: The script rewrites the translation files, if you are not using version control then keep backups!*
