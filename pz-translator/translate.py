import re
import sys
import json
import time

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from deep_translator import GoogleTranslator

class Translator:

    QUOTED_TEXT_REGEX = re.compile(r'"([^"]+)"')  # Matches text inside quotes

    def __init__(self, translate_path: Path, no41: bool):
        self.root = translate_path
        self.source_lang = "EN"

        # Find the mods folder
        mods_path = self.find_mods_folder(translate_path)
        self.language_info_file = self.select_language_info(translate_path, mods_path)

        # **Skip processing if -no41 is set and this folder would use LanguagesInfo_b41.json**
        if no41 and self.language_info_file == "LanguagesInfo_b41.json":
            print(f"Skipping: {self.clean_path_for_display(translate_path)} (-no41)")
            self.languages = []
            return

        self.language_info = self.load_language_info(self.language_info_file)
        self.languages = [lang for lang in self.language_info if lang != "EN"]


    def load_language_info(self, file_name):
        """
        Loads the language info JSON file dynamically.
        """
        json_path = Path(__file__).parent.parent / file_name
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)


    def clean_path_for_display(self, path):
        return re.sub(r'.*?\\mods\\', '', str(path))  # Keep only the part after 'mods'


    def find_mods_folder(self, path):
        """
        Finds the 'mods' folder by traversing up from the given path.
        """
        while path and path.name.lower() != "mods":
            path = path.parent
            if path == path.parent:  # Stop if we reach the root
                return None
        return path


    def select_language_info(self, translate_path, mods_path):
        """
        Determines which LanguagesInfo file to use based on the Translate folder depth.
        """
        if not mods_path:
            return "LanguagesInfo.json"  # Default if no mods folder is found

        depth = len(translate_path.relative_to(mods_path).parts)

        if depth == 5:
            return "LanguagesInfo_b41.json"
        return "LanguagesInfo.json"


    def get_translation_path(self, lang_id: str):
        return self.root / lang_id


    def batch_translate(self, texts, lang):
        """
        Translates a batch of quoted strings only.
        """
        unique_texts = list(set(texts))  # Remove duplicates
        if not unique_texts:
            return {}

        translator = GoogleTranslator(source="en", target=self.language_info[lang]["tr_code"])
        try:
            translations = translator.translate_batch(unique_texts)  # Batch API call
            if not translations or len(translations) != len(unique_texts):
                print(f"Warning: Batch translation failed for {lang}")
                return {}
            return dict(zip(unique_texts, translations))
        except Exception as e:
            print(f"Translation Error ({lang}): {e}")
            return {}


    def extract_and_translate(self, text, lang):
        """
        Extracts only text inside quotes and translates it.
        Non-quoted text remains unchanged.
        """
        quoted_texts = self.QUOTED_TEXT_REGEX.findall(text)  # Extract only quoted content

        if not quoted_texts:
            return text  # No quotes found, return as-is

        translated_map = self.batch_translate(quoted_texts, lang)

        return self.QUOTED_TEXT_REGEX.sub(lambda m: f'"{translated_map.get(m.group(1), m.group(1))}"', text)


    def get_charset(self, lang):
        """
        Gets encoding charset for the language from the selected LanguagesInfo file.
        Defaults to UTF-8 if missing.
        """
        return self.language_info.get(lang, {}).get("charset", "UTF-8")


    def translate_file(self, file, lang, lang_path, charset):
        """
        Translates only quoted phrases within a file and always overwrites existing translations.
        """
        relative_path = file.relative_to(self.get_translation_path(self.source_lang))
        source_filename = relative_path.name
        dest_filename = source_filename.replace("_EN", f"_{lang}")

        dest_file = lang_path / relative_path.with_name(dest_filename)

        with open(file, "r", encoding="utf-8") as f:
            source_text = f.read().strip()

        if not source_text:
            return  # Skip empty files

        translated_text = self.extract_and_translate(source_text, lang)
        translated_text = translated_text.replace("_EN", f"_{lang}")

        if translated_text.strip() == source_text.strip():
            print(f"Skipping (No Change): {source_filename} -> {dest_filename} ({lang})")
            return  # Skip writing if no changes were made

        with open(dest_file, "w", encoding=charset, errors="replace") as f:
            f.write(translated_text)

        # print(f"Overwritten: {source_filename} -> {dest_filename} ({lang})")


    def translate_files(self):
        """
        Translates all files inside the 'Translate' directory, only printing if files are actually processed.
        """
        source_path = self.get_translation_path(self.source_lang)
        if not source_path.is_dir() or not self.languages:
            return  # Skip processing if no languages are set (e.g., due to -no41)

        files = list(source_path.rglob("*.txt"))  # Collect files before printing

        if not files:
            return  # Skip printing if there are no translatable files

        # Clean up path for display
        display_path = self.clean_path_for_display(self.root)

        # Start timing
        start_time = time.perf_counter()

        print(f"Processing: {display_path} using {self.language_info_file}")

        for lang in self.languages:
            lang_path = self.get_translation_path(lang)
            lang_path.mkdir(exist_ok=True)
            charset = self.get_charset(lang)

            with ThreadPoolExecutor() as executor:
                executor.map(lambda file: self.translate_file(file, lang, lang_path, charset), files)

        # End timing
        elapsed_time = (time.perf_counter() - start_time) * 1000  # Convert to milliseconds
        print(f"Completed: {display_path} in {elapsed_time:.2f} ms")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python translate.py <directory_path> [-no41]")
        sys.exit(1)

    base_dir = Path(sys.argv[1]).resolve()
    no41 = "-no41" in sys.argv  # Detect the -no41 flag

    if not base_dir.is_dir():
        print(f"Invalid directory: {base_dir}")
        sys.exit(1)

    total_start_time = time.perf_counter()  # Start total time tracking

    for translate_dir in base_dir.rglob("Translate"):
        translator = Translator(translate_dir, no41)
        translator.translate_files()

    total_elapsed_time = (time.perf_counter() - total_start_time) * 1000  # Convert to ms
    print(f"\nTotal Processing Time: {total_elapsed_time:.2f} ms")


