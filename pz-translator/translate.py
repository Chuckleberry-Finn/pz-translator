import re
import sys
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from deep_translator import GoogleTranslator

class Translator:
    QUOTED_TEXT_REGEX = re.compile(r'"([^"]+)"')
    TAG_MODULATION = [
        ("<", "{<{"), (">", "}>}"),  # Protect HTML-like tags
        ("[", "{[{"), ("]", "}]}"),  # Protect square brackets
        ("%1", "{%1}"), ("%2", "{%2}"), ("%3", "{%3}"),  # Protect placeholders
    ]

    def __init__(self, translate_path: Path, no41: bool):
        self.root = translate_path
        self.source_lang = "EN"
        self.api_call_count = 0  # Track API calls

        mods_path = self.find_mods_folder(translate_path)
        self.language_info_file = self.select_language_info(translate_path, mods_path)

        if no41 and self.language_info_file == "LanguagesInfo_b41.json":
            print(f"Skipping: {self.clean_path_for_display(translate_path)} (-no41)")
            self.languages = []
            return

        self.language_info = self.load_language_info(self.language_info_file)
        self.languages = [lang for lang in self.language_info if lang != "EN"]
        self.translation_cache = {}

    def modulate_tags(self, text: str) -> str:
        for k, v in self.TAG_MODULATION:
            text = text.replace(k, v)
        return text

    def demodulate_tags(self, text: str) -> str:
        for k, v in self.TAG_MODULATION:
            text = text.replace(v, k)
        return text

    def load_language_info(self, file_name):
        json_path = Path(__file__).parent.parent / file_name
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def clean_path_for_display(self, path):
        return re.sub(r'.*?\\mods\\', '', str(path))

    def find_mods_folder(self, path):
        while path and path.name.lower() != "mods":
            path = path.parent
            if path == path.parent:
                return None
        return path

    def select_language_info(self, translate_path, mods_path):
        if not mods_path:
            return "LanguagesInfo.json"
        depth = len(translate_path.relative_to(mods_path).parts)
        return "LanguagesInfo_b41.json" if depth == 5 else "LanguagesInfo.json"

    def get_translation_path(self, lang_id: str):
        return self.root / lang_id

    def batch_translate(self, texts, lang):
        if not texts:
            return {}

        self.api_call_count += 1  # Increment API call count
        cached_translations = {text: self.translation_cache.get((lang, text)) for text in texts}
        texts_to_translate = [text for text, trans in cached_translations.items() if trans is None]

        if texts_to_translate:
            try:
                translator = GoogleTranslator(source="en", target=self.language_info[lang]["tr_code"])
                translations = translator.translate_batch(texts_to_translate)

                if not translations:
                    raise ValueError("Google API returned an empty response.")

                for original, translated in zip(texts_to_translate, translations):
                    self.translation_cache[(lang, original)] = translated
                    cached_translations[original] = translated
            except Exception as e:
                print(f"Translation Error ({lang}): {e}")
                return None

        return cached_translations


    def extract_and_translate(self, text, lang):
        quoted_texts = self.QUOTED_TEXT_REGEX.findall(text)
        if not quoted_texts:
            return text

        translated_map = self.batch_translate(quoted_texts, lang)
        if translated_map is None:
            return None

        return self.QUOTED_TEXT_REGEX.sub(lambda m: translated_map.get(m.group(1), m.group(1)), text)

    def get_charset(self, lang):
        return self.language_info.get(lang, {}).get("charset", "UTF-8")

    def translate_files(self):
        source_path = self.get_translation_path(self.source_lang)
        if not source_path.is_dir() or not self.languages:
            return

        files = list(source_path.rglob("*.txt"))
        if not files:
            return

        total_start_time = time.perf_counter()
        print(f"Processing: {self.clean_path_for_display(self.root)} using {self.language_info_file}")

        def process_language(lang):
            lang_start_time = time.perf_counter()
            lang_path = self.get_translation_path(lang)
            lang_path.mkdir(exist_ok=True)
            text_map = {}

            for file in files:
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        for line in f:
                            quoted_texts = self.QUOTED_TEXT_REGEX.findall(line)
                            for text in quoted_texts:
                                text_map[text] = text_map.get(text, set())
                                text_map[text].add(file)
                except Exception as e:
                    print(f"Error reading {file.name}: {e}")

            translated_map = self.batch_translate(list(text_map.keys()), lang)
            if translated_map is None:
                return

            def process_file(file):
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        lines = f.readlines()

                    translated_lines = []
                    for line in lines:
                        header_match = re.match(r'^(.+?)_EN\s*=\s*{', line)
                        if header_match:
                            translated_lines.append(f"{header_match.group(1)}_{lang} = {{\n")
                            continue
                        translated_lines.append(self.QUOTED_TEXT_REGEX.sub(lambda m: f'"{translated_map.get(m.group(1), m.group(1))}"', line))

                    dest_file = lang_path / file.relative_to(source_path).with_name(file.stem.replace("_EN", f"_{lang}") + file.suffix)
                    with open(dest_file, "w", encoding="utf-8", errors="replace") as f:
                        f.writelines(translated_lines)
                except Exception as e:
                    print(f"Error writing {file.name}: {e}")

            with ThreadPoolExecutor() as file_executor:
                file_futures = [file_executor.submit(process_file, file) for file in files]
                for future in as_completed(file_futures):
                    future.result()

            lang_elapsed_time = (time.perf_counter() - lang_start_time) * 1000
            print(f"Completed: {self.clean_path_for_display(self.root)} - {lang} in {lang_elapsed_time:.2f} ms")

        with ThreadPoolExecutor() as lang_executor:
            lang_futures = [lang_executor.submit(process_language, lang) for lang in self.languages]
            for future in as_completed(lang_futures):
                future.result()

        print(f"Total API calls made: {self.api_call_count}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python translate.py <directory_path> [-no41]")
        sys.exit(1)

    base_dir = Path(sys.argv[1]).resolve()
    no41 = "-no41" in sys.argv

    if not base_dir.is_dir():
        print(f"Invalid directory: {base_dir}")
        sys.exit(1)

    total_start_time = time.perf_counter()
    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(Translator(translate_dir, no41).translate_files)
            for translate_dir in base_dir.rglob("Translate")
        ]

        for future in as_completed(futures):
            future.result()

    total_elapsed_time = (time.perf_counter() - total_start_time) * 1000
    print(f"\nTotal Processing Time: {total_elapsed_time:.2f} ms")
