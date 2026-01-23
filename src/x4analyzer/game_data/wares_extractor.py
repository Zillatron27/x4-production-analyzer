"""Extract production data from X4 game wares.xml files."""

import json
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Union

from .catalog_reader import CatalogReader
from .text_resolver import TextResolver

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


def safe_float(value: Union[str, None], default: float = 0.0) -> float:
    """Safely convert a value to float, returning default on failure."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        logger.debug(f"Could not convert '{value}' to float, using default {default}")
        return default


@dataclass
class ResourceRequirement:
    """A resource required for production."""
    ware_id: str
    amount: int


@dataclass
class ProductionMethod:
    """A production method for a ware."""
    method_id: str  # e.g., "default", "teladi", etc.
    time_seconds: float  # Production cycle time in seconds
    amount_produced: int  # Amount produced per cycle
    resources: List[ResourceRequirement] = field(default_factory=list)

    @property
    def units_per_hour(self) -> float:
        """Calculate production rate in units per hour."""
        if self.time_seconds <= 0:
            return 0.0
        cycles_per_hour = 3600 / self.time_seconds
        return cycles_per_hour * self.amount_produced

    def resource_per_hour(self, ware_id: str) -> float:
        """Calculate consumption rate of a resource in units per hour."""
        if self.time_seconds <= 0:
            return 0.0
        cycles_per_hour = 3600 / self.time_seconds
        for res in self.resources:
            if res.ware_id == ware_id:
                return cycles_per_hour * res.amount
        return 0.0


@dataclass
class ProductionData:
    """Production data for a ware."""
    ware_id: str
    name: str
    transport_class: str = "container"  # container, solid, liquid, etc.
    volume: int = 1  # Volume per unit
    price_min: int = 0
    price_avg: int = 0
    price_max: int = 0
    production_methods: List[ProductionMethod] = field(default_factory=list)

    @property
    def default_method(self) -> Optional[ProductionMethod]:
        """Get the default production method."""
        for method in self.production_methods:
            if method.method_id == "default":
                return method
        return self.production_methods[0] if self.production_methods else None

    def get_production_rate(self, method_id: str = "default") -> float:
        """Get production rate in units per hour for a method."""
        for method in self.production_methods:
            if method.method_id == method_id:
                return method.units_per_hour
        return self.default_method.units_per_hour if self.default_method else 0.0


class WaresExtractor:
    """Extract production data from X4 game files."""

    WARES_PATH = "libraries/wares.xml"
    CACHE_FILENAME = "wares_cache.json"

    def __init__(self, game_directory: Path, cache_directory: Optional[Path] = None):
        """Initialize with game and cache directories."""
        self.game_dir = Path(game_directory)
        self.cache_dir = Path(cache_directory) if cache_directory else Path.home() / ".cache" / "x4analyzer"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.wares: Dict[str, ProductionData] = {}
        self._loaded = False
        self._text_resolver: Optional[TextResolver] = None

    def _get_cache_path(self) -> Path:
        """Get the cache file path."""
        return self.cache_dir / self.CACHE_FILENAME

    def _get_game_version_fingerprint(self) -> str:
        """
        Get a fingerprint based on key game file timestamps.

        This allows us to detect when the game has been updated
        and the cache needs refreshing.
        """
        key_files = [
            self.game_dir / "01.cat",
            self.game_dir / "08.cat",  # Contains wares.xml
        ]

        timestamps = []
        for f in key_files:
            if f.exists():
                timestamps.append(f"{f.name}:{f.stat().st_mtime}")

        return "|".join(sorted(timestamps))

    def _load_from_cache(self) -> bool:
        """Try to load wares data from cache."""
        cache_path = self._get_cache_path()

        if not cache_path.exists():
            return False

        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)

            # Check if cache is for the same game directory
            if data.get("game_directory") != str(self.game_dir):
                logger.info("Cache is for different game directory, will re-extract")
                return False

            # Check if game version has changed
            cached_fingerprint = data.get("game_version_fingerprint", "")
            current_fingerprint = self._get_game_version_fingerprint()
            if cached_fingerprint != current_fingerprint:
                logger.info("Game files have been updated, will re-extract")
                return False

            # Load wares
            for ware_id, ware_data in data.get("wares", {}).items():
                methods = []
                for m in ware_data.get("production_methods", []):
                    resources = [ResourceRequirement(**r) for r in m.get("resources", [])]
                    methods.append(ProductionMethod(
                        method_id=m["method_id"],
                        time_seconds=m["time_seconds"],
                        amount_produced=m["amount_produced"],
                        resources=resources
                    ))

                self.wares[ware_id] = ProductionData(
                    ware_id=ware_data["ware_id"],
                    name=ware_data["name"],
                    transport_class=ware_data.get("transport_class", "container"),
                    volume=ware_data.get("volume", 1),
                    price_min=ware_data.get("price_min", 0),
                    price_avg=ware_data.get("price_avg", 0),
                    price_max=ware_data.get("price_max", 0),
                    production_methods=methods
                )

            logger.info(f"Loaded {len(self.wares)} wares from cache")
            self._loaded = True
            return True

        except (json.JSONDecodeError, KeyError, TypeError, IOError, OSError) as e:
            logger.warning(f"Failed to load cache: {e}")
            return False

    def _save_to_cache(self):
        """Save wares data to cache."""
        cache_path = self._get_cache_path()

        # Convert to serializable format
        wares_data = {}
        for ware_id, ware in self.wares.items():
            methods_data = []
            for m in ware.production_methods:
                methods_data.append({
                    "method_id": m.method_id,
                    "time_seconds": m.time_seconds,
                    "amount_produced": m.amount_produced,
                    "resources": [asdict(r) for r in m.resources]
                })

            wares_data[ware_id] = {
                "ware_id": ware.ware_id,
                "name": ware.name,
                "transport_class": ware.transport_class,
                "volume": ware.volume,
                "price_min": ware.price_min,
                "price_avg": ware.price_avg,
                "price_max": ware.price_max,
                "production_methods": methods_data
            }

        data = {
            "game_directory": str(self.game_dir),
            "game_version_fingerprint": self._get_game_version_fingerprint(),
            "wares": wares_data
        }

        try:
            with open(cache_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.wares)} wares to cache")
        except (IOError, OSError, TypeError) as e:
            logger.error(f"Failed to save cache: {e}")

    def extract(self, force_reload: bool = False) -> Dict[str, ProductionData]:
        """
        Extract production data from game files.

        Args:
            force_reload: If True, bypass cache and re-extract from game files

        Returns:
            Dictionary mapping ware_id to ProductionData
        """
        if self._loaded and not force_reload:
            return self.wares

        # Try cache first
        if not force_reload and self._load_from_cache():
            return self.wares

        # Extract from game files
        logger.info("Extracting wares data from game files...")

        try:
            catalog = CatalogReader(self.game_dir)

            # Initialize text resolver for ware names
            self._text_resolver = TextResolver(catalog)

            # Read wares.xml - use base file to avoid getting diff patches
            wares_xml = catalog.read_base_text_file(self.WARES_PATH)
            if not wares_xml:
                # Try regular read as fallback
                wares_xml = catalog.read_text_file(self.WARES_PATH)
            if not wares_xml:
                # Try direct file access (for unpacked game files)
                direct_path = self.game_dir / self.WARES_PATH
                if direct_path.exists():
                    wares_xml = direct_path.read_text()
                else:
                    logger.error("Could not find wares.xml in game files")
                    return self.wares

            self._parse_wares_xml(wares_xml)
            self._loaded = True

            # Save to cache
            self._save_to_cache()

        except (ET.ParseError, IOError, OSError) as e:
            logger.error(f"Failed to extract wares data: {e}")

        return self.wares

    def _parse_wares_xml(self, xml_content: str):
        """Parse wares.xml content with XXE protection."""
        # Create a parser that disables external entity resolution for security
        # While game files are trusted, this is defensive coding practice
        parser = ET.XMLParser()
        # Note: Python's xml.etree.ElementTree doesn't support external entities
        # by default (unlike some other XML libraries), but we explicitly use
        # a parser instance for clarity and future-proofing
        root = ET.fromstring(xml_content, parser=parser)

        for ware_elem in root.findall(".//ware"):
            try:
                ware_data = self._parse_ware(ware_elem)
                if ware_data:
                    self.wares[ware_data.ware_id] = ware_data
            except Exception as e:
                ware_id = ware_elem.get("id", "unknown")
                logger.warning(f"Failed to parse ware {ware_id}: {e}")

        logger.info(f"Parsed {len(self.wares)} wares from wares.xml")

    def _parse_ware(self, ware_elem: ET.Element) -> Optional[ProductionData]:
        """Parse a single ware element."""
        ware_id = ware_elem.get("id")
        if not ware_id:
            return None

        # Get name and resolve text reference if needed
        name_ref = ware_elem.get("name", ware_id)
        if self._text_resolver and name_ref.startswith("{"):
            name = self._text_resolver.resolve(name_ref)
        else:
            name = name_ref

        # Get transport class
        transport_class = ware_elem.get("transport", "container")

        # Get volume (safe conversion)
        volume = safe_int(ware_elem.get("volume"), default=1)

        # Get price info (safe conversions)
        price_elem = ware_elem.find("price")
        price_min = price_avg = price_max = 0
        if price_elem is not None:
            price_min = safe_int(price_elem.get("min"), default=0)
            price_avg = safe_int(price_elem.get("average"), default=0)
            price_max = safe_int(price_elem.get("max"), default=0)

        # Get production methods
        # X4 structure: <ware><production time="X" amount="Y" method="Z"><primary><ware .../></primary></production></ware>
        production_methods = []
        for production_elem in ware_elem.findall("production"):
            method = self._parse_production_method(production_elem)
            if method:
                production_methods.append(method)

        return ProductionData(
            ware_id=ware_id,
            name=name,
            transport_class=transport_class,
            volume=volume,
            price_min=price_min,
            price_avg=price_avg,
            price_max=price_max,
            production_methods=production_methods
        )

    def _parse_production_method(self, production_elem: ET.Element) -> Optional[ProductionMethod]:
        """Parse a production element."""
        method_id = production_elem.get("method", "default")

        # Get production time in seconds (safe conversion)
        time_seconds = safe_float(production_elem.get("time"), default=0.0)

        # Get amount produced (safe conversion)
        amount = safe_int(production_elem.get("amount"), default=1)

        # Get resource requirements from <primary> child
        resources = []
        primary_elem = production_elem.find("primary")
        if primary_elem is not None:
            for ware_elem in primary_elem.findall("ware"):
                res_ware_id = ware_elem.get("ware")
                res_amount = safe_int(ware_elem.get("amount"), default=1)
                if res_ware_id:
                    resources.append(ResourceRequirement(
                        ware_id=res_ware_id,
                        amount=res_amount
                    ))

        return ProductionMethod(
            method_id=method_id,
            time_seconds=time_seconds,
            amount_produced=amount,
            resources=resources
        )

    def get_production_rate(self, ware_id: str, method: str = "default") -> float:
        """
        Get production rate for a ware in units per hour.

        Args:
            ware_id: The ware identifier
            method: Production method (default: "default")

        Returns:
            Production rate in units per hour, or 0 if unknown
        """
        if not self._loaded:
            self.extract()

        ware = self.wares.get(ware_id.lower())
        if ware:
            return ware.get_production_rate(method)
        return 0.0

    def get_consumption_rate(self, ware_id: str, produced_ware_id: str, method: str = "default") -> float:
        """
        Get consumption rate of a ware when producing another ware.

        Args:
            ware_id: The consumed ware identifier
            produced_ware_id: The ware being produced
            method: Production method

        Returns:
            Consumption rate in units per hour, or 0 if unknown
        """
        if not self._loaded:
            self.extract()

        produced_ware = self.wares.get(produced_ware_id.lower())
        if produced_ware:
            for m in produced_ware.production_methods:
                if m.method_id == method or method == "default":
                    return m.resource_per_hour(ware_id.lower())
        return 0.0

    def list_produced_wares(self) -> List[str]:
        """List all wares that can be produced."""
        if not self._loaded:
            self.extract()

        return [ware_id for ware_id, ware in self.wares.items()
                if ware.production_methods]

    def get_ware_info(self, ware_id: str) -> Optional[ProductionData]:
        """Get full production data for a ware."""
        if not self._loaded:
            self.extract()

        return self.wares.get(ware_id.lower())
