"""Resolve X4 text references from localization files."""

import logging
import re
from typing import Dict, Optional

from .catalog_reader import CatalogReader

logger = logging.getLogger("x4analyzer.game_data")


class TextResolver:
    """
    Resolve X4 text references like {20201,701} to actual text.

    X4 uses references in format {pageId,textId} that map to
    localization files (t/XXXX-lYYY.xml).
    """

    # Language codes - 44 is English
    LANGUAGE_ENGLISH = 44

    def __init__(self, catalog: CatalogReader, language: int = LANGUAGE_ENGLISH):
        """Initialize with a catalog reader and language code."""
        self.catalog = catalog
        self.language = language
        self._texts: Dict[int, Dict[int, str]] = {}  # page_id -> {text_id -> text}
        self._loaded = False

    def _load_texts(self):
        """Load text data from localization files."""
        if self._loaded:
            return

        # Find all localization files for our language
        lang_suffix = f"-l{self.language:03d}.xml"

        # Get list of text files
        all_files = self.catalog.list_files("t/*.xml")
        text_files = [f for f in all_files if lang_suffix in f and not f.endswith('.sig')]

        logger.info(f"Loading {len(text_files)} localization files for language {self.language}")

        for text_file in text_files:
            self._load_text_file(text_file)

        self._loaded = True
        logger.info(f"Loaded {sum(len(p) for p in self._texts.values())} text entries from {len(self._texts)} pages")

    def _load_text_file(self, filename: str):
        """Load a single text file."""
        content = self.catalog.read_base_text_file(filename)
        if not content:
            return

        # Parse pages and texts using regex (faster than full XML parsing for this)
        page_pattern = re.compile(r'<page id="(\d+)"[^>]*>(.*?)</page>', re.DOTALL)
        text_pattern = re.compile(r'<t id="(\d+)">(.*?)</t>', re.DOTALL)

        for page_match in page_pattern.finditer(content):
            page_id = int(page_match.group(1))
            page_content = page_match.group(2)

            if page_id not in self._texts:
                self._texts[page_id] = {}

            for text_match in text_pattern.finditer(page_content):
                text_id = int(text_match.group(1))
                text = text_match.group(2)

                # Clean up the text (unescape XML entities)
                text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
                text = text.replace('&apos;', "'").replace('&quot;', '"')

                self._texts[page_id][text_id] = text

    def resolve(self, reference: str) -> str:
        """
        Resolve a text reference to actual text.

        Args:
            reference: Text reference like "{20201,701}" or plain text

        Returns:
            Resolved text, or the original reference if not found
        """
        if not reference:
            return reference

        # Check if it's a reference format {pageId,textId}
        match = re.match(r'\{(\d+),(\d+)\}', reference)
        if not match:
            return reference

        self._load_texts()

        page_id = int(match.group(1))
        text_id = int(match.group(2))

        page = self._texts.get(page_id)
        if page:
            text = page.get(text_id)
            if text:
                return text

        # Not found, return original reference
        logger.debug(f"Text reference not found: {reference}")
        return reference

    def get_text(self, page_id: int, text_id: int) -> Optional[str]:
        """Get text by page and text ID directly."""
        self._load_texts()

        page = self._texts.get(page_id)
        if page:
            return page.get(text_id)
        return None
