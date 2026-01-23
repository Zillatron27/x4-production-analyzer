"""Configuration management for X4 Analyzer."""

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger("x4analyzer.config")


@dataclass
class X4Config:
    """Configuration settings for X4 Analyzer."""

    # Paths
    save_directory: Optional[str] = None
    game_directory: Optional[str] = None
    last_save_file: Optional[str] = None

    # Cache settings
    cache_directory: Optional[str] = None
    game_data_version: Optional[str] = None  # Game version when data was extracted

    @classmethod
    def get_config_path(cls) -> Path:
        """Get the path to the config file."""
        config_dir = Path.home() / ".config" / "x4analyzer"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "config.json"

    @classmethod
    def get_cache_path(cls) -> Path:
        """Get the path to the cache directory."""
        cache_dir = Path.home() / ".cache" / "x4analyzer"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    @classmethod
    def load(cls) -> "X4Config":
        """Load config from file or return defaults."""
        config_path = cls.get_config_path()

        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    data = json.load(f)
                logger.info(f"Loaded config from {config_path}")
                return cls(**data)
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to load config: {e}")

        return cls()

    def save(self):
        """Save config to file."""
        config_path = self.get_config_path()

        with open(config_path, 'w') as f:
            json.dump(asdict(self), f, indent=2)

        logger.info(f"Saved config to {config_path}")


class PathDetector:
    """Auto-detect X4 game and save file paths."""

    # Common X4 save file locations
    SAVE_PATHS = [
        # Windows default
        Path.home() / "Documents" / "Egosoft" / "X4" / "save",
        # Linux native (direct)
        Path.home() / ".config" / "EgoSoft" / "X4" / "save",
        # Steam Proton (Linux)
        Path.home() / ".steam" / "steam" / "steamapps" / "compatdata" / "392160" / "pfx" / "drive_c" / "users" / "steamuser" / "Documents" / "Egosoft" / "X4" / "save",
        Path.home() / ".local" / "share" / "Steam" / "steamapps" / "compatdata" / "392160" / "pfx" / "drive_c" / "users" / "steamuser" / "Documents" / "Egosoft" / "X4" / "save",
        # Flatpak Steam
        Path.home() / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam" / "steamapps" / "compatdata" / "392160" / "pfx" / "drive_c" / "users" / "steamuser" / "Documents" / "Egosoft" / "X4" / "save",
    ]

    # Base directories to scan for account-specific save folders
    SAVE_BASE_DIRS = [
        Path.home() / ".config" / "EgoSoft" / "X4",  # Linux: ~/.config/EgoSoft/X4/{AccountID}/save
    ]

    # Common X4 game installation locations
    GAME_PATHS = [
        # Steam (Windows)
        Path("C:/Program Files (x86)/Steam/steamapps/common/X4 Foundations"),
        Path("C:/Program Files/Steam/steamapps/common/X4 Foundations"),
        # Steam (Linux native)
        Path.home() / ".steam" / "steam" / "steamapps" / "common" / "X4 Foundations",
        Path.home() / ".local" / "share" / "Steam" / "steamapps" / "common" / "X4 Foundations",
        # Flatpak Steam
        Path.home() / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam" / "steamapps" / "common" / "X4 Foundations",
        # GOG (Windows)
        Path("C:/GOG Games/X4 Foundations"),
        Path("C:/Program Files/GOG Galaxy/Games/X4 Foundations"),
        # GOG (Linux)
        Path.home() / "GOG Games" / "X4 Foundations",
    ]

    @classmethod
    def find_save_directory(cls) -> Optional[Path]:
        """Find the X4 save directory."""
        # First check direct paths
        for path in cls.SAVE_PATHS:
            if path.exists() and path.is_dir():
                # Check if it contains save files (gzipped or plain XML)
                save_files = (list(path.glob("save_*.xml.gz")) +
                              list(path.glob("quicksave*.xml.gz")) +
                              list(path.glob("save_*.xml")) +
                              list(path.glob("quicksave*.xml")))
                if save_files:
                    logger.info(f"Found save directory: {path}")
                    return path

        # Then scan base directories for account-specific folders
        # Linux stores saves in ~/.config/EgoSoft/X4/{Steam3AccountID}/save
        for base_dir in cls.SAVE_BASE_DIRS:
            if base_dir.exists() and base_dir.is_dir():
                # Look for any subdirectory that contains a save folder
                for subdir in base_dir.iterdir():
                    if subdir.is_dir():
                        save_path = subdir / "save"
                        if save_path.exists() and save_path.is_dir():
                            save_files = (list(save_path.glob("save_*.xml.gz")) +
                                          list(save_path.glob("quicksave*.xml.gz")) +
                                          list(save_path.glob("save_*.xml")) +
                                          list(save_path.glob("quicksave*.xml")))
                            if save_files:
                                logger.info(f"Found save directory: {save_path}")
                                return save_path

        logger.warning("Could not auto-detect save directory")
        return None

    @classmethod
    def find_game_directory(cls) -> Optional[Path]:
        """Find the X4 game installation directory."""
        for path in cls.GAME_PATHS:
            if path.exists() and path.is_dir():
                # Verify it's an X4 installation by checking for expected files
                if cls._verify_game_directory(path):
                    logger.info(f"Found game directory: {path}")
                    return path

        logger.warning("Could not auto-detect game directory")
        return None

    @classmethod
    def _verify_game_directory(cls, path: Path) -> bool:
        """Verify that a directory is a valid X4 installation."""
        # Check for key files that should exist in X4 installation
        expected_files = [
            path / "01.cat",  # Main game data catalog
            path / "X4.exe",  # Windows executable
        ]
        expected_files_linux = [
            path / "01.cat",
            path / "X4",  # Linux executable
        ]

        # Check Windows paths
        if all(f.exists() for f in expected_files):
            return True

        # Check Linux paths
        if all(f.exists() for f in expected_files_linux):
            return True

        # At minimum, check for catalog files
        cat_files = list(path.glob("*.cat"))
        return len(cat_files) > 0

    @classmethod
    def find_recent_saves(cls, save_dir: Path, limit: int = 10) -> List[Path]:
        """Find the most recent save files in a directory."""
        if not save_dir or not save_dir.exists():
            return []

        save_files = list(save_dir.glob("save_*.xml.gz")) + list(save_dir.glob("quicksave*.xml.gz"))

        # Sort by modification time, most recent first
        save_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        return save_files[:limit]

    @classmethod
    def get_save_file_info(cls, save_path: Path) -> dict:
        """Get information about a save file."""
        import time

        stat = save_path.stat()
        return {
            "name": save_path.name,
            "path": str(save_path),
            "size_mb": stat.st_size / (1024 * 1024),
            "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
        }


class ConfigManager:
    """Manage configuration and path detection."""

    def __init__(self):
        self.config = X4Config.load()
        self._auto_detect_paths()

    def _auto_detect_paths(self):
        """Auto-detect paths if not configured."""
        changed = False

        # Auto-detect save directory
        if not self.config.save_directory or not Path(self.config.save_directory).exists():
            save_dir = PathDetector.find_save_directory()
            if save_dir:
                self.config.save_directory = str(save_dir)
                changed = True

        # Auto-detect game directory
        if not self.config.game_directory or not Path(self.config.game_directory).exists():
            game_dir = PathDetector.find_game_directory()
            if game_dir:
                self.config.game_directory = str(game_dir)
                changed = True

        # Set default cache directory
        if not self.config.cache_directory:
            self.config.cache_directory = str(X4Config.get_cache_path())
            changed = True

        if changed:
            self.config.save()

    def get_save_directory(self) -> Optional[Path]:
        """Get the configured save directory."""
        if self.config.save_directory:
            return Path(self.config.save_directory)
        return None

    def get_game_directory(self) -> Optional[Path]:
        """Get the configured game directory."""
        if self.config.game_directory:
            return Path(self.config.game_directory)
        return None

    def get_recent_saves(self, limit: int = 10) -> List[dict]:
        """Get list of recent save files with info."""
        save_dir = self.get_save_directory()
        if not save_dir:
            return []

        saves = PathDetector.find_recent_saves(save_dir, limit)
        return [PathDetector.get_save_file_info(s) for s in saves]

    def set_save_directory(self, path: str):
        """Manually set the save directory."""
        self.config.save_directory = path
        self.config.save()

    def set_game_directory(self, path: str):
        """Manually set the game directory."""
        self.config.game_directory = path
        self.config.save()

    def set_last_save(self, path: str):
        """Record the last used save file."""
        self.config.last_save_file = path
        self.config.save()

    def get_last_save(self) -> Optional[Path]:
        """Get the last used save file if it exists."""
        if self.config.last_save_file:
            path = Path(self.config.last_save_file)
            if path.exists():
                return path
        return None
