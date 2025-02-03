import re
import sys
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from deep_translator import GoogleTranslator

class Translator:
    QUOTED_TEXT_REGEX = re.compile(r'"([^"]+)"')

    def __init__(self, translate_path: Path, no41: bool):
        self.root = translate_path
        self.source_lang = "EN"

        mods_path = self.find_mods_folder(translate_path)
        self.language_info_file = self.select_language_info(translate_path, mods_path)

        if no41 and self.language_info_file == "LanguagesInfo_b41.json":
            print(f"Skipping: {self.clean_path_for_display(translate_path)} (-no41)")
            self.languages = []
            return

        self.language_info = self.load_language_info(self.language_info_file)
        self.languages = [lang for lang in self.language_info if lang != "EN"]
        self.translation_cache = {}  # Cache to store translations

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
        """Batch translation with caching and error handling."""
        unique_texts = list(set(texts))
        if not unique_texts:
            return {}

        cached_translations = {text: self.translation_cache.get((lang, text)) for text in unique_texts}
        texts_to_translate = [text for text, trans in cached_translations.items() if trans is None]

        if texts_to_translate:
            translator = GoogleTranslator(source="en", target=self.language_info[lang]["tr_code"])
            try:
                translations = translator.translate_batch(texts_to_translate)
                if translations is None or any(t is None for t in translations):
                    raise ValueError("Google API returned None for some translations.")

                for original, translated in zip(texts_to_translate, translations):
                    self.translation_cache[(lang, original)] = translated
                    cached_translations[original] = translated
            except Exception as e:
                print(f"Translation Error ({lang}): {e}")
                return None  # **Return None if translation fails**

        return cached_translations


    def extract_and_translate(self, text, lang):
        """Extracts quoted text, translates it, and replaces it in the original text."""
        quoted_texts = self.QUOTED_TEXT_REGEX.findall(text)
        if not quoted_texts:
            return text

        translated_map = self.batch_translate(quoted_texts, lang)

        if translated_map is None:  # **Detect API failure**
            return None

        return self.QUOTED_TEXT_REGEX.sub(lambda m: f'"{translated_map.get(m.group(1), m.group(1))}"', text)


    def get_charset(self, lang):
        return self.language_info.get(lang, {}).get("charset", "UTF-8")

    def translate_file(self, file, lang, lang_path, charset):
        """Skips writing files if API translation fails."""
        relative_path = file.relative_to(self.get_translation_path(self.source_lang))
        source_filename = relative_path.name
        dest_filename = source_filename.replace("_EN", f"_{lang}")
        dest_file = lang_path / relative_path.with_name(dest_filename)

        try:
            with open(file, "r", encoding="utf-8") as f:
                source_text = f.read().strip()
            if not source_text:
                return  # Skip empty files

            translated_text = self.extract_and_translate(source_text, lang)

            # **Detect API failure and skip writing**
            if translated_text is None:
                print(f"Skipping file due to API translation failure: {self.clean_path_for_display(file)}")
                return

            with open(dest_file, "w", encoding=charset, errors="replace") as f:
                f.write(translated_text)
        except Exception as e:
            print(f"Error processing {self.clean_path_for_display(file)}: {e}")



    def translate_files(self):
        """Optimized file processing with parallel execution."""
        source_path = self.get_translation_path(self.source_lang)
        if not source_path.is_dir() or not self.languages:
            return

        files = list(source_path.rglob("*.txt"))
        if not files:
            return

        start_time = time.perf_counter()
        print(f"Processing: {self.clean_path_for_display(self.root)} using {self.language_info_file}")

        with ThreadPoolExecutor() as executor:
            futures = []
            for lang in self.languages:
                lang_path = self.get_translation_path(lang)
                lang_path.mkdir(exist_ok=True)
                charset = self.get_charset(lang)

                for file in files:
                    futures.append(executor.submit(self.translate_file, file, lang, lang_path, charset))

            for future in as_completed(futures):
                future.result()  # Ensure exceptions are raised if any

        elapsed_time = (time.perf_counter() - start_time) * 1000
        print(f"Completed: {self.clean_path_for_display(self.root)} in {elapsed_time:.2f} ms")

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
        futures = [executor.submit(Translator(translate_dir, no41).translate_files) for translate_dir in base_dir.rglob("Translate")]

        for future in as_completed(futures):
            future.result()

    total_elapsed_time = (time.perf_counter() - total_start_time) * 1000
    print(f"\nTotal Processing Time: {total_elapsed_time:.2f} ms")