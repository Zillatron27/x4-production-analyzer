"""Extract ship cargo capacity data from X4 game files."""

import json
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Union

from .catalog_reader import CatalogReader

logger = logging.getLogger("x4analyzer.game_data")


def safe_int(value: Union[str, None], default: int = 0) -> int:
    """Safely convert a value to int, returning default on failure."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        logger.debug(f"Could not convert '{value}' to int, using default {default}")
        return default


@dataclass
class ShipStorageData:
    """Storage data for a ship."""
    macro_name: str  # e.g., "storage_par_m_miner_liquid_01_a_macro"
    cargo_capacity: int  # Max cargo in units
    cargo_tags: str  # "solid", "liquid", "container", etc.


@dataclass
class ShipData:
    """Ship data extracted from game files."""
    macro_name: str  # e.g., "ship_par_m_miner_liquid_01_a_macro"
    ship_class: str  # "ship_s", "ship_m", "ship_l", "ship_xl"
    ship_type: str  # "miner", "freighter", "fighter", etc.
    purpose: str  # "mine", "trade", "fight", etc.
    cargo_capacity: int  # Total cargo capacity
    cargo_tags: str  # What it can carry: "solid", "liquid", "container"
    storage_macro: str  # Reference to storage macro
    race: str  # "argon", "paranid", "teladi", etc.


class ShipsExtractor:
    """Extract ship data from X4 game files."""

    CACHE_FILENAME = "ships_cache.json"

    def __init__(self, game_directory: Path, cache_directory: Optional[Path] = None):
        """Initialize with game and cache directories."""
        self.game_dir = Path(game_directory)
        self.cache_dir = Path(cache_directory) if cache_directory else Path.home() / ".cache" / "x4analyzer"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.ships: Dict[str, ShipData] = {}
        self.storage: Dict[str, ShipStorageData] = {}
        self._loaded = False

    def _get_cache_path(self) -> Path:
        """Get the cache file path."""
        return self.cache_dir / self.CACHE_FILENAME

    def _get_game_version_fingerprint(self) -> str:
        """Get a fingerprint based on key game file timestamps."""
        key_files = [
            self.game_dir / "01.cat",
            self.game_dir / "08.cat",
        ]
        timestamps = []
        for f in key_files:
            if f.exists():
                timestamps.append(f"{f.name}:{f.stat().st_mtime}")
        return "|".join(sorted(timestamps))

    def _load_from_cache(self) -> bool:
        """Try to load ship data from cache."""
        cache_path = self._get_cache_path()

        if not cache_path.exists():
            return False

        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)

            if data.get("game_directory") != str(self.game_dir):
                logger.info("Cache is for different game directory, will re-extract")
                return False

            cached_fingerprint = data.get("game_version_fingerprint", "")
            current_fingerprint = self._get_game_version_fingerprint()
            if cached_fingerprint != current_fingerprint:
                logger.info("Game files have been updated, will re-extract")
                return False

            # Load ships
            for macro_name, ship_data in data.get("ships", {}).items():
                self.ships[macro_name] = ShipData(**ship_data)

            # Load storage
            for macro_name, storage_data in data.get("storage", {}).items():
                self.storage[macro_name] = ShipStorageData(**storage_data)

            logger.info(f"Loaded {len(self.ships)} ships and {len(self.storage)} storage macros from cache")
            self._loaded = True
            return True

        except (json.JSONDecodeError, KeyError, TypeError, IOError, OSError) as e:
            logger.warning(f"Failed to load cache: {e}")
            return False

    def _save_to_cache(self):
        """Save ship data to cache."""
        cache_path = self._get_cache_path()

        data = {
            "game_directory": str(self.game_dir),
            "game_version_fingerprint": self._get_game_version_fingerprint(),
            "ships": {name: asdict(ship) for name, ship in self.ships.items()},
            "storage": {name: asdict(storage) for name, storage in self.storage.items()}
        }

        try:
            with open(cache_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.ships)} ships to cache")
        except (IOError, OSError, TypeError) as e:
            logger.error(f"Failed to save cache: {e}")

    def extract(self, force_reload: bool = False) -> Dict[str, ShipData]:
        """
        Extract ship data from game files.

        Args:
            force_reload: If True, bypass cache and re-extract from game files

        Returns:
            Dictionary mapping ship macro name to ShipData
        """
        if self._loaded and not force_reload:
            return self.ships

        if not force_reload and self._load_from_cache():
            return self.ships

        logger.info("Extracting ship data from game files...")

        try:
            catalog = CatalogReader(self.game_dir)

            # First, extract all storage macros to get cargo capacities
            self._extract_storage_macros(catalog)

            # Then extract ship macros
            self._extract_ship_macros(catalog)

            self._loaded = True
            self._save_to_cache()

        except (ET.ParseError, IOError, OSError) as e:
            logger.error(f"Failed to extract ship data: {e}")

        return self.ships

    def _extract_storage_macros(self, catalog: CatalogReader):
        """Extract all storage macros to get cargo capacities."""
        # Find all storage macro XML files (not station storage)
        storage_files = catalog.list_files('*storage*macro*.xml')
        storage_files = [f for f in storage_files if 'station' not in f.lower() and f.endswith('.xml')]

        logger.info(f"Found {len(storage_files)} storage macro files")

        for filepath in storage_files:
            try:
                content = catalog.read_text_file(filepath)
                if not content:
                    continue

                # Parse with explicit parser for XXE protection
                parser = ET.XMLParser()
                root = ET.fromstring(content, parser=parser)
                for macro_elem in root.findall(".//macro[@class='storage']"):
                    storage_data = self._parse_storage_macro(macro_elem)
                    if storage_data:
                        self.storage[storage_data.macro_name] = storage_data

            except (ET.ParseError, ValueError) as e:
                logger.debug(f"Failed to parse storage macro {filepath}: {e}")

        logger.info(f"Extracted {len(self.storage)} storage macros")

    def _parse_storage_macro(self, macro_elem: ET.Element) -> Optional[ShipStorageData]:
        """Parse a storage macro element."""
        macro_name = macro_elem.get("name")
        if not macro_name:
            return None

        cargo_elem = macro_elem.find(".//cargo")
        if cargo_elem is None:
            return None

        cargo_max = safe_int(cargo_elem.get("max"), default=0)
        cargo_tags = cargo_elem.get("tags", "container")

        return ShipStorageData(
            macro_name=macro_name,
            cargo_capacity=cargo_max,
            cargo_tags=cargo_tags
        )

    def _extract_ship_macros(self, catalog: CatalogReader):
        """Extract all ship macros."""
        # Find ship macro files in units directories
        ship_files = []
        for size in ['size_xs', 'size_s', 'size_m', 'size_l', 'size_xl']:
            pattern = f'assets/units/{size}/macros/ship_*.xml'
            ship_files.extend(catalog.list_files(pattern))

        # Also check legacy location
        ship_files.extend(catalog.list_files('assets/legacy/*/macros/ship_*.xml'))

        # Filter to only XML files (not signatures)
        ship_files = [f for f in ship_files if f.endswith('.xml') and not f.endswith('.sig')]

        logger.info(f"Found {len(ship_files)} ship macro files")

        for filepath in ship_files:
            try:
                content = catalog.read_text_file(filepath)
                if not content:
                    continue

                # Parse with explicit parser for XXE protection
                parser = ET.XMLParser()
                root = ET.fromstring(content, parser=parser)
                for macro_elem in root.findall(".//macro"):
                    ship_class = macro_elem.get("class", "")
                    if ship_class.startswith("ship_"):
                        ship_data = self._parse_ship_macro(macro_elem)
                        if ship_data:
                            self.ships[ship_data.macro_name] = ship_data

            except (ET.ParseError, ValueError) as e:
                logger.debug(f"Failed to parse ship macro {filepath}: {e}")

        logger.info(f"Extracted {len(self.ships)} ship macros")

    def _parse_ship_macro(self, macro_elem: ET.Element) -> Optional[ShipData]:
        """Parse a ship macro element."""
        macro_name = macro_elem.get("name")
        ship_class = macro_elem.get("class", "")

        if not macro_name or not ship_class.startswith("ship_"):
            return None

        # Get properties
        props = macro_elem.find("properties")
        if props is None:
            return None

        # Get ship type from <ship type="..."/>
        ship_elem = props.find("ship")
        ship_type = ship_elem.get("type", "unknown") if ship_elem is not None else "unknown"

        # Get purpose from <purpose primary="..."/>
        purpose_elem = props.find("purpose")
        purpose = purpose_elem.get("primary", "") if purpose_elem is not None else ""

        # Get race from <identification makerrace="..."/>
        ident_elem = props.find("identification")
        race = ident_elem.get("makerrace", "unknown") if ident_elem is not None else "unknown"

        # Find storage connection to get cargo capacity
        # Look for "con_storage" connections (not "shipstorage" which is for docking smaller ships)
        storage_macro = ""
        cargo_capacity = 0
        cargo_tags = "container"

        connections = macro_elem.find("connections")
        if connections is not None:
            for conn in connections.findall("connection"):
                conn_ref = conn.get("ref", "")
                # Match "con_storage01", "con_storage02", etc. but not "con_shipstorage"
                if conn_ref.startswith("con_storage") and "shipstorage" not in conn_ref.lower():
                    macro_ref = conn.find("macro")
                    if macro_ref is not None:
                        storage_macro = macro_ref.get("ref", "")
                        # Look up storage data
                        if storage_macro in self.storage:
                            storage_data = self.storage[storage_macro]
                            cargo_capacity = storage_data.cargo_capacity
                            cargo_tags = storage_data.cargo_tags
                        break

        return ShipData(
            macro_name=macro_name,
            ship_class=ship_class,
            ship_type=ship_type,
            purpose=purpose,
            cargo_capacity=cargo_capacity,
            cargo_tags=cargo_tags,
            storage_macro=storage_macro,
            race=race
        )

    def get_ship_cargo_capacity(self, ship_macro: str) -> int:
        """
        Get cargo capacity for a ship macro.

        Args:
            ship_macro: The ship macro name (e.g., "ship_par_m_miner_liquid_01_a_macro")

        Returns:
            Cargo capacity in units, or 0 if unknown
        """
        if not self._loaded:
            self.extract()

        # Normalize macro name (remove _macro suffix if present, lowercase)
        normalized = ship_macro.lower()
        if not normalized.endswith("_macro"):
            normalized += "_macro"

        ship = self.ships.get(normalized)
        if ship:
            return ship.cargo_capacity

        # Try without _macro suffix
        if normalized.endswith("_macro"):
            ship = self.ships.get(normalized[:-6])
            if ship:
                return ship.cargo_capacity

        return 0

    def get_ship_info(self, ship_macro: str) -> Optional[ShipData]:
        """Get full ship data for a macro."""
        if not self._loaded:
            self.extract()

        normalized = ship_macro.lower()
        if not normalized.endswith("_macro"):
            normalized += "_macro"

        return self.ships.get(normalized)

    def get_ships_by_type(self, ship_type: str) -> List[ShipData]:
        """Get all ships of a specific type (e.g., 'miner', 'freighter')."""
        if not self._loaded:
            self.extract()

        return [ship for ship in self.ships.values() if ship.ship_type == ship_type]

    def get_miner_ships(self) -> List[ShipData]:
        """Get all miner ships."""
        return self.get_ships_by_type("miner")
