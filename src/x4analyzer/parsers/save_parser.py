"""Parser for X4 save files (XML.gz format)."""

import gzip
import xml.etree.ElementTree as ET
import time
import random
from pathlib import Path
from typing import Optional, Callable
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn


# Fun flavor text for loading sequence
FLAVOR_TEXTS = [
    "RETICULATING SPLINES...",
    "CALIBRATING FLUX CAPACITORS...",
    "OPTIMIZING JUMP ROUTES...",
    "CALCULATING HYPERSPACE COORDINATES...",
    "ANALYZING SUBSPACE FIELDS...",
    "CHANNELING TACHYONS...",
    "INITIALIZING QUANTUM PROCESSORS...",
    "SYNCHRONIZING TRADE ALGORITHMS...",
    "MAPPING SECTOR NETWORKS...",
    "DECRYPTING STATION MANIFESTS...",
    "TRIANGULATING GATE POSITIONS...",
    "PARSING GALACTIC ECONOMICS...",
    "INDEXING PRODUCTION CHAINS...",
    "SCANNING CARGO MANIFESTS...",
    "COMPILING TRADE ROUTES...",
    "ANALYZING WARE DEPENDENCIES...",
]


class SaveFileParser:
    """Handles decompression and parsing of X4 save files."""

    def __init__(self, file_path: str):
        """Initialize parser with save file path."""
        self.file_path = Path(file_path)
        self.root: Optional[ET.Element] = None

    def parse(self, progress_callback: Optional[Callable[[str], None]] = None) -> ET.Element:
        """
        Parse the save file and return the XML root element.

        Args:
            progress_callback: Optional callback for progress updates

        Returns:
            XML root element

        Raises:
            FileNotFoundError: If save file doesn't exist
            gzip.BadGzipFile: If file is not a valid gzip file
            ET.ParseError: If XML is malformed
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"Save file not found: {self.file_path}")

        # Decompress
        if progress_callback:
            progress_callback("Decompressing save file...")

        try:
            with gzip.open(self.file_path, 'rb') as f:
                xml_content = f.read()
        except gzip.BadGzipFile:
            # Maybe it's not compressed, try reading as plain XML
            if progress_callback:
                progress_callback("File not compressed, reading as plain XML...")
            with open(self.file_path, 'rb') as f:
                xml_content = f.read()

        # Parse XML
        if progress_callback:
            progress_callback("Parsing XML...")

        self.root = ET.fromstring(xml_content)

        if progress_callback:
            progress_callback("Parsing complete!")

        return self.root

    def parse_with_progress(self) -> ET.Element:
        """Parse with rich progress display and flavor text."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task("Loading save file...", total=None)

            # Show a few random flavor texts before parsing
            flavor_samples = random.sample(FLAVOR_TEXTS, min(3, len(FLAVOR_TEXTS)))
            for flavor in flavor_samples:
                progress.update(task, description=f"[cyan]{flavor}[/cyan]")
                time.sleep(1.0)

            def update_progress(msg: str):
                progress.update(task, description=msg)

            return self.parse(update_progress)

    @staticmethod
    def find_default_save() -> Optional[Path]:
        """
        Attempt to find the default X4 save file location.

        Returns:
            Path to save directory if found, None otherwise
        """
        # Common X4 save locations
        possible_paths = [
            Path.home() / "Documents" / "Egosoft" / "X4" / "save",
            Path.home() / ".steam" / "steam" / "steamapps" / "compatdata" / "392160" / "pfx" / "drive_c" / "users" / "steamuser" / "Documents" / "Egosoft" / "X4" / "save",
            Path("/home") / "user" / ".local" / "share" / "Steam" / "steamapps" / "compatdata" / "392160" / "pfx" / "drive_c" / "users" / "steamuser" / "Documents" / "Egosoft" / "X4" / "save",
        ]

        for path in possible_paths:
            if path.exists() and path.is_dir():
                # Find most recent save file
                save_files = list(path.glob("save_*.xml.gz"))
                if save_files:
                    return max(save_files, key=lambda p: p.stat().st_mtime)

        return None
