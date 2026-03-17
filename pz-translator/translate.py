import re
import sys
import json
import time
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from deep_translator import GoogleTranslator

sys.stdout.reconfigure(encoding="utf-8")

def parse_txt(text: str, source_path: Path = None) -> dict:
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
            close = value.find('"', 1)
            while close != -1 and value[close - 1] == '\\':
                close = value.find('"', close + 1)
            if close == -1:
                name = source_path.name if source_path else '?'
                print(f"    [!] No closing quote for '{key}' in {name} — used as-is")
                value = value[1:].replace('\\"', '"')
            else:
                value = value[1:close].replace('\\"', '"')

        if key in entries and source_path:
            print(f"    [!] Duplicate key '{key}' in {source_path.name}")
        entries[key] = value
    return entries


def json_output_name(txt_stem: str, language_info: dict) -> str:
    """
    IG_UI_EN    → IG_UI.json
    ItemName_FR → ItemName.json
    SurvivorNames → SurvivorNames.json
    """
    parts = txt_stem.split("_")
    if len(parts) > 1 and parts[-1].upper() in language_info:
        return "_".join(parts[:-1]) + ".json"
    return txt_stem + ".json"


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


class Translator:
    QUOTED_TEXT_REGEX = re.compile(r'"([^"]+)"')
    TAG_MODULATION = [
        ("<",  "{<{"), (">",  "}>}"),
        ("[",  "{[{"), ("]",  "}]}"),
        ("%1", "{%1}"), ("%2", "{%2}"), ("%3", "{%3}"),
        ("%4", "{%4}"), ("%5", "{%5}"),
    ]

    def __init__(self, translate_path: Path, enabled_languages: list,
                 source_lang: str = "EN", skip_existing: bool = True):
        self.root           = translate_path
        self.source_lang    = source_lang
        self.skip_existing  = skip_existing
        self.api_call_count = 0

        self.language_info = self._load_language_info()
        self.languages = [
            lang for lang in self.language_info
            if lang != self.source_lang and (not enabled_languages or lang in enabled_languages)
        ]
        self.translation_cache = {}

    @staticmethod
    def is_b41_folder(path: Path) -> bool:
        current = path
        while current != current.parent:
            if current.name.lower() == "mods":
                return len(path.relative_to(current).parts) == 5
            current = current.parent
        return False

    def _load_language_info(self) -> dict:
        with open(Path(__file__).parent / "LanguagesInfo_b42.json", "r", encoding="utf-8") as f:
            return json.load(f)

    def _get_tr_code(self, lang: str) -> str:
        return self.language_info.get(lang, {}).get("tr_code", lang.lower())

    def _get_translation_path(self, lang_id: str) -> Path:
        return self.root / lang_id

    def _modulate(self, text: str) -> str:
        for k, v in self.TAG_MODULATION:
            text = text.replace(k, v)
        return text

    def _demodulate(self, text: str) -> str:
        for k, v in self.TAG_MODULATION:
            text = text.replace(v, k)
        return text

    def _batch_translate(self, texts: list, lang: str) -> dict | None:
        if not texts:
            return {}

        self.api_call_count += 1
        result       = {}
        to_translate = []

        for text in texts:
            cached = self.translation_cache.get((lang, text))
            if cached is not None:
                result[text] = cached
            else:
                to_translate.append(text)

        if to_translate:
            try:
                translator = GoogleTranslator(
                    source=self._get_tr_code(self.source_lang),
                    target=self._get_tr_code(lang)
                )
                translations = translator.translate_batch([self._modulate(t) for t in to_translate])

                if not translations:
                    raise ValueError("Empty response from Google Translate.")

                for original, raw in zip(to_translate, translations):
                    final = self._demodulate(raw)
                    self.translation_cache[(lang, original)] = final
                    result[original] = final
            except Exception as e:
                print(f"    [!] {lang} — translation error: {e}")
                return None

        return result

    def _translate_json_files(self, source_path: Path, json_files: list):
        print(f"\n[B42]  {self.root.name}  ({len(json_files)} file(s))")
        total_start = time.perf_counter()

        def process_language(lang: str):
            lang_start    = time.perf_counter()
            lang_path     = self._get_translation_path(lang)
            lang_path.mkdir(exist_ok=True)
            total_written = 0
            total_skipped = 0

            for src_file in json_files:
                dest_file = lang_path / src_file.relative_to(source_path)
                dest_file.parent.mkdir(parents=True, exist_ok=True)

                try:
                    with open(src_file, "r", encoding="utf-8-sig") as f:
                        src_data: dict = json.load(f)
                except Exception as e:
                    print(f"    [!] Could not read {src_file.name}: {e}")
                    continue

                existing = {}
                if self.skip_existing and dest_file.exists():
                    try:
                        with open(dest_file, "r", encoding="utf-8-sig") as f:
                            existing = json.load(f)
                    except Exception:
                        pass

                to_translate = [
                    value for key, value in src_data.items()
                    if isinstance(value, str) and value.strip()
                    and not (self.skip_existing and key in existing)
                ]
                skipped = sum(1 for key in src_data if self.skip_existing and key in existing)

                translated_values = self._batch_translate(to_translate, lang)
                if translated_values is None:
                    print(f"    [!] {src_file.name} — skipped for {lang} (translation error)")
                    continue

                output = {}
                for key, value in src_data.items():
                    if self.skip_existing and key in existing:
                        output[key] = existing[key]
                    elif isinstance(value, str):
                        output[key] = translated_values.get(value, value)
                    else:
                        output[key] = value

                dest_file.write_text(
                    json.dumps(output, indent=4, ensure_ascii=False),
                    encoding="utf-8"
                )
                total_written += len(to_translate)
                total_skipped += skipped

            elapsed   = (time.perf_counter() - lang_start) * 1000
            lang_name = self.language_info.get(lang, {}).get("text", "")
            skip_note = f"  ({total_skipped} existing preserved)" if total_skipped else ""
            print(f"  {lang:<6}  {lang_name:<24}  {total_written} translated{skip_note}   {elapsed:.0f}ms")

        with ThreadPoolExecutor() as executor:
            for future in as_completed([executor.submit(process_language, lang) for lang in self.languages]):
                future.result()

        elapsed = (time.perf_counter() - total_start) * 1000
        print(f"  Done — {len(self.languages)} language(s) in {elapsed/1000:.1f}s  |  {self.api_call_count} API call(s)")

    def _translate_txt_to_json(self, source_path: Path, txt_files: list):
        print(f"\n[B42]  {self.root.name}  ({len(txt_files)} file(s), converting txt → json)")
        total_start = time.perf_counter()

        parsed_files: dict[Path, dict] = {}
        for txt_path in txt_files:
            try:
                entries = parse_txt(txt_path.read_text(encoding="utf-8-sig"), txt_path)
                if entries:
                    parsed_files[txt_path] = entries
            except Exception as e:
                print(f"    [!] Could not read {txt_path.name}: {e}")

        def process_language(lang: str):
            lang_start    = time.perf_counter()
            lang_path     = self._get_translation_path(lang)
            lang_path.mkdir(exist_ok=True)
            total_written = 0
            total_skipped = 0

            for txt_path, entries in parsed_files.items():
                dest_file = lang_path / json_output_name(txt_path.stem, self.language_info)
                entries   = strip_key_prefixes(entries, dest_file.stem)

                existing = {}
                if self.skip_existing and dest_file.exists():
                    try:
                        with open(dest_file, "r", encoding="utf-8-sig") as f:
                            existing = json.load(f)
                    except Exception:
                        pass

                to_translate = [
                    value for key, value in entries.items()
                    if isinstance(value, str) and value.strip()
                    and not (self.skip_existing and key in existing)
                ]
                skipped = sum(1 for key in entries if self.skip_existing and key in existing)

                translated_values = self._batch_translate(to_translate, lang)
                if translated_values is None:
                    print(f"    [!] {txt_path.name} — skipped for {lang} (translation error)")
                    continue

                output = {}
                for key, value in entries.items():
                    if self.skip_existing and key in existing:
                        output[key] = existing[key]
                    else:
                        output[key] = translated_values.get(value, value)

                dest_file.write_text(
                    json.dumps(output, indent=4, ensure_ascii=False),
                    encoding="utf-8"
                )
                total_written += len(to_translate)
                total_skipped += skipped

            elapsed   = (time.perf_counter() - lang_start) * 1000
            lang_name = self.language_info.get(lang, {}).get("text", "")
            skip_note = f"  ({total_skipped} existing preserved)" if total_skipped else ""
            print(f"  {lang:<6}  {lang_name:<24}  {total_written} translated{skip_note}   {elapsed:.0f}ms")

        with ThreadPoolExecutor() as executor:
            for future in as_completed([executor.submit(process_language, lang) for lang in self.languages]):
                future.result()

        elapsed = (time.perf_counter() - total_start) * 1000
        print(f"  Done — {len(self.languages)} language(s) in {elapsed/1000:.1f}s  |  {self.api_call_count} API call(s)")

    def translate_files(self):
        source_path = self._get_translation_path(self.source_lang)
        if not source_path.is_dir() or not self.languages:
            return

        json_files = list(source_path.rglob("*.json"))
        txt_files  = list(source_path.rglob("*.txt"))

        if json_files:
            self._translate_json_files(source_path, json_files)
        elif txt_files:
            self._translate_txt_to_json(source_path, txt_files)
        else:
            print(f"  [!] No translation files found in {source_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PZ Translation Tool")
    parser.add_argument("directory")
    parser.add_argument("-source",    default="EN")
    parser.add_argument("-overwrite", action="store_true")
    parser.add_argument("-languages", nargs="*", default=[])

    args     = parser.parse_args()
    base_dir = Path(args.directory).resolve()

    if not base_dir.is_dir():
        print(f"Invalid directory: {base_dir}")
        sys.exit(1)

    langs_display = ', '.join(args.languages) if args.languages else "all"
    print(f"Source: {args.source}  |  Languages: {langs_display}  |  Overwrite: {args.overwrite}")

    total_start = time.perf_counter()
    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(
                Translator(
                    d, args.languages,
                    source_lang=args.source,
                    skip_existing=not args.overwrite
                ).translate_files
            )
            for d in base_dir.rglob("Translate")
            if d.is_dir() and not Translator.is_b41_folder(d)
        ]
        for future in as_completed(futures):
            future.result()

    print(f"\nFinished in {(time.perf_counter() - total_start):.1f}s")
