"""Reader for X4 catalog (.cat) and data (.dat) file pairs."""

import logging
import struct
from pathlib import Path
from typing import Dict, Optional, List, BinaryIO
from dataclasses import dataclass

logger = logging.getLogger("x4analyzer.game_data")


@dataclass
class CatalogEntry:
    """An entry in a catalog file."""
    filename: str
    offset: int
    size: int
    timestamp: int


class CatalogReader:
    """
    Read X4 catalog (.cat) and data (.dat) file pairs.

    X4 uses paired .cat/.dat files where:
    - .cat contains an index of files (filename, offset, size, timestamp)
    - .dat contains the actual file data at the specified offsets

    Multiple catalog pairs exist (01.cat/01.dat through extensions)
    and later catalogs override earlier ones.
    """

    def __init__(self, game_directory: Path):
        """Initialize with game directory path."""
        self.game_dir = Path(game_directory)
        self.entries: Dict[str, tuple[CatalogEntry, Path]] = {}  # filename -> (entry, dat_path)
        self._load_catalogs()

    def _load_catalogs(self):
        """Load all catalog files in order."""
        # Find all .cat files and sort them
        cat_files = sorted(self.game_dir.glob("*.cat"))

        # Also check extensions folder
        extensions_dir = self.game_dir / "extensions"
        if extensions_dir.exists():
            for ext_dir in extensions_dir.iterdir():
                if ext_dir.is_dir():
                    cat_files.extend(sorted(ext_dir.glob("*.cat")))

        for cat_file in cat_files:
            self._load_catalog(cat_file)

        logger.info(f"Loaded {len(self.entries)} files from {len(cat_files)} catalogs")

    def _load_catalog(self, cat_path: Path):
        """Load a single catalog file."""
        dat_path = cat_path.with_suffix(".dat")

        if not dat_path.exists():
            logger.warning(f"Missing .dat file for {cat_path}")
            return

        try:
            with open(cat_path, 'rb') as f:
                content = f.read()

            # Parse catalog entries
            # Format: Each line is "filename size timestamp\n"
            # The offset is implicit (cumulative from start of dat file)
            entries = self._parse_catalog_content(content)

            # Track current offset in dat file
            offset = 0
            for entry in entries:
                entry.offset = offset
                offset += entry.size

                # Store entry (later catalogs override earlier ones)
                self.entries[entry.filename] = (entry, dat_path)

        except Exception as e:
            logger.error(f"Failed to load catalog {cat_path}: {e}")

    def _parse_catalog_content(self, content: bytes) -> List[CatalogEntry]:
        """Parse catalog content into entries."""
        entries = []

        try:
            # Catalogs are text files with entries like:
            # filename size timestamp hash
            text = content.decode('utf-8', errors='replace')

            for line in text.strip().split('\n'):
                if not line.strip():
                    continue

                parts = line.strip().split()
                if len(parts) >= 3:
                    filename = parts[0]
                    size = int(parts[1])
                    timestamp = int(parts[2])

                    entries.append(CatalogEntry(
                        filename=filename,
                        offset=0,  # Will be set later
                        size=size,
                        timestamp=timestamp
                    ))
        except Exception as e:
            logger.error(f"Failed to parse catalog content: {e}")

        return entries

    def list_files(self, pattern: str = None) -> List[str]:
        """List all files in the catalogs, optionally filtered by pattern."""
        files = list(self.entries.keys())

        if pattern:
            import fnmatch
            files = [f for f in files if fnmatch.fnmatch(f, pattern)]

        return sorted(files)

    def file_exists(self, filename: str) -> bool:
        """Check if a file exists in the catalogs."""
        # Normalize path separators
        normalized = filename.replace('\\', '/').lower()

        for entry_name in self.entries.keys():
            if entry_name.replace('\\', '/').lower() == normalized:
                return True
        return False

    def read_file(self, filename: str) -> Optional[bytes]:
        """Read a file from the catalogs."""
        # Normalize path separators
        normalized = filename.replace('\\', '/').lower()

        # Find matching entry
        entry_info = None
        for entry_name, info in self.entries.items():
            if entry_name.replace('\\', '/').lower() == normalized:
                entry_info = info
                break

        if not entry_info:
            logger.warning(f"File not found in catalogs: {filename}")
            return None

        entry, dat_path = entry_info

        try:
            with open(dat_path, 'rb') as f:
                f.seek(entry.offset)
                data = f.read(entry.size)

            # Check if data is compressed (gzip)
            if data[:2] == b'\x1f\x8b':
                import gzip
                data = gzip.decompress(data)

            return data

        except Exception as e:
            logger.error(f"Failed to read {filename} from {dat_path}: {e}")
            return None

    def read_text_file(self, filename: str) -> Optional[str]:
        """Read a text file from the catalogs."""
        data = self.read_file(filename)
        if data:
            try:
                return data.decode('utf-8')
            except UnicodeDecodeError:
                return data.decode('latin-1')
        return None
