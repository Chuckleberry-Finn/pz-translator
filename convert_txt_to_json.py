import os
import re
import json
import sys
from pathlib import Path

ALL_LANG_CODES = {
    "AR", "CA", "CH", "CN", "CS", "DA", "DE", "EN", "ES", "FI",
    "FR", "HU", "ID", "IT", "JP", "KO", "NL", "NO", "PH", "PL",
    "PT", "PTBR", "RO", "RU", "TH", "TR", "UA",
}

AMBER     = "\033[38;5;214m" # handled issues — corrected automatically
ORANGE    = "\033[38;5;208m" # malformed values — skipped
GOLDENROD = "\033[38;5;220m" # warnings — duplicates, no entries
RED       = "\033[31m"       # errors   — unreadable/unwritable files
RESET     = "\033[0m"

def handled(msg: str):   print(f"{AMBER}{msg}{RESET}")
def malformed(msg: str): print(f"{ORANGE}{msg}{RESET}")
def warn(msg: str):      print(f"{GOLDENROD}{msg}{RESET}")
def error(msg: str):     print(f"{RED}{msg}{RESET}")


def is_b41_folder(path: Path) -> bool:
    current = path
    while current != current.parent:
        if current.name.lower() == "mods":
            return len(path.relative_to(current).parts) == 5
        current = current.parent
    return False


def read_txt(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def parse_txt(text: str, path: Path) -> dict:
    match = re.search(r"\{(.*)\}", text, re.DOTALL)
    if not match:
        return {}

    entries = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("--") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key   = key.strip()
        value = value.strip()

        if value.startswith('"'):
            # Find the closing quote, ignoring escaped quotes inside the value
            close = value.find('"', 1)
            while close != -1 and value[close - 1] == '\\':
                close = value.find('"', close + 1)
            if close == -1:
                malformed(f"  [!] No closing quote for '{key}' in {path.name} — used as-is")
                malformed(f"      Got: {value}")
                value = value[1:].replace('\\"', '"')
            else:
                # Check for trailing period after the closing quote
                trailing = value[close + 1:].lstrip(", ")
                if trailing.startswith("."):
                    handled(f"  [~] Trailing period corrected for '{key}' in {path.name}")
                value = value[1:close].replace('\\"', '"')

        if key in entries:
            warn(f"  [!] Duplicate key '{key}' in {path.name}")
        entries[key] = value
    return entries


KEY_PREFIX_STRIP = {
    "EvolvedRecipeName": "EvolvedRecipeName_",
    "Recipes":           "Recipe_",
    "ItemName":          "ItemName_",
}


def strip_key_prefixes(entries: dict, json_stem: str) -> dict:
    prefix = KEY_PREFIX_STRIP.get(json_stem)
    if not prefix:
        return entries
    return {
        (k[len(prefix):] if k.startswith(prefix) else k): v
        for k, v in entries.items()
    }


def json_output_name(txt_stem: str) -> str:
    parts = txt_stem.split("_")
    if len(parts) > 1 and parts[-1].upper() in ALL_LANG_CODES:
        return "_".join(parts[:-1]) + ".json"
    return txt_stem + ".json"


def convert(root: Path):
    converted = 0
    skipped   = 0

    for translate_dir in root.rglob("Translate"):
        if not translate_dir.is_dir():
            continue
        if is_b41_folder(translate_dir):
            print(f"[B41 skipped]  {translate_dir}")
            continue

        print(f"\n[B42]  {translate_dir}")

        for txt_path in translate_dir.rglob("*.txt"):
            try:
                entries = parse_txt(read_txt(txt_path), txt_path)
            except Exception as e:
                error(f"  [!] Could not read {txt_path.name}: {e}")
                skipped += 1
                continue

            if not entries:
                warn(f"  [!] No entries found in {txt_path.name} — skipped")
                skipped += 1
                continue

            json_path = txt_path.parent / json_output_name(txt_path.stem)
            entries   = strip_key_prefixes(entries, json_path.stem)

            try:
                json_path.write_text(
                    json.dumps(entries, indent=4, ensure_ascii=False),
                    encoding="utf-8"
                )
                print(f"  {txt_path.name}  ->  {json_path.name}  ({len(entries)} keys)")
                converted += 1
            except Exception as e:
                error(f"  [!] Could not write {json_path.name}: {e}")
                skipped += 1

    print(f"\nDone — {converted} file(s) converted, {skipped} skipped.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        target = Path(__file__).parent
    else:
        target = Path(sys.argv[1]).resolve()

    if not target.is_dir():
        error(f"Invalid directory: {target}")
        sys.exit(1)

    print(f"Scanning: {target}\n")
    convert(target)
