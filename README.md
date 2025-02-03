## pz-translator <sup><sub><sup><sub>2.0</sup></sub></sup></sub>
### Automated batch-capable Project Zomboid translations.
#### <sup>[original concept](https://github.com/Poltergeist-PZ-Modding/pz-translator) by [Poltergeist](https://github.com/Poltergeist-ix).</sup>

## Requirements

- Python 3.11
- [deep_translator](https://pypi.org/project/deep-translator/) <sup><sub>*(Developed with 1.11.4)*</sup></sub>


## How to use

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
# 

### command line
example for windows, you can also write this into a cmd file for shortcut.
```
py "repository/pz-translator/translate.py" "relative-path to translate"
```

### VSCode task

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


## Text Translator

Deep translator supports different translators, you can find more information at: [https://pypi.org/project/deep-translator/](https://pypi.org/project/deep-translator/)

#
### *WARINIG: The script rewrites the translation files, if you are not using version control then keep backups!*
