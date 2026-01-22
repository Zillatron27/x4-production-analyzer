"""Main application entry point."""

import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table

from .parsers.streaming_parser import StreamingParser
from .analyzers.production_analyzer import ProductionAnalyzer
from .ui.dashboard import Dashboard
from .ui.views import ViewRenderer
from .config import ConfigManager


class X4Analyzer:
    """Main application class."""

    def __init__(self):
        self.console = Console()
        self.config_manager = ConfigManager()
        self.empire = None
        self.analyzer = None
        self.dashboard = None
        self.views = None
        self._current_save_path = None
        self._wares_extractor = None

    def load_save_file(self, file_path: str = None):
        """Load and parse a save file."""
        # Try to find save file if not provided
        if not file_path:
            file_path = self._select_save_file()

        if not file_path:
            self.console.print("[red]No file specified[/red]")
            return False

        try:
            # Parse save file using memory-efficient streaming parser
            self.console.print("[cyan]Parsing save file (streaming mode)...[/cyan]")
            parser = StreamingParser(file_path)

            def progress_callback(msg, count):
                self.console.print(f"[cyan]{msg}[/cyan]")

            self.empire = parser.parse(progress_callback)

            # Analyze
            self.console.print("[cyan]Analyzing production data...[/cyan]")
            self.analyzer = ProductionAnalyzer(self.empire)

            # Try to load game data for accurate production rates
            self._load_game_data()

            # Setup UI
            self.dashboard = Dashboard(self.empire, self.analyzer)
            self.views = ViewRenderer(self.empire, self.analyzer,
                                      config_manager=self.config_manager,
                                      save_file_path=file_path)
            self._current_save_path = file_path

            self.console.print("[green]Load complete![/green]\n")

            # Remember this save file
            self.config_manager.set_last_save(file_path)

            self.console.input("Press Enter to continue...")

            return True

        except FileNotFoundError as e:
            self.console.print(f"[red]Error: {e}[/red]")
            return False
        except Exception as e:
            self.console.print(f"[red]Failed to load save file: {e}[/red]")
            if "--debug" in sys.argv:
                raise
            return False

    def _select_save_file(self) -> str:
        """Display save file selection menu."""
        self.console.print("[cyan]X4 Save File Selection[/cyan]\n")

        # Check for last used save
        last_save = self.config_manager.get_last_save()
        if last_save:
            self.console.print(f"[dim]Last used: {last_save.name}[/dim]")
            use_last = self.console.input("Use last save file? (Y/n): ").strip().lower()
            if use_last != 'n':
                return str(last_save)
            self.console.print()

        # Get recent saves
        recent_saves = self.config_manager.get_recent_saves(10)

        if recent_saves:
            self.console.print("[bold]Recent Save Files:[/bold]\n")

            table = Table(show_header=True, header_style="bold")
            table.add_column("#", style="cyan", width=3)
            table.add_column("Save File", style="green")
            table.add_column("Size", justify="right")
            table.add_column("Modified", style="dim")

            for i, save in enumerate(recent_saves, 1):
                table.add_row(
                    str(i),
                    save["name"],
                    f"{save['size_mb']:.1f} MB",
                    save["modified"]
                )

            self.console.print(table)
            self.console.print()

            choice = self.console.input("Enter number or path (or press Enter for #1): ").strip()

            if not choice:
                return recent_saves[0]["path"]

            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(recent_saves):
                    return recent_saves[idx]["path"]
                else:
                    self.console.print("[red]Invalid selection[/red]")
                    return None

            # Assume it's a path
            return choice

        else:
            self.console.print("[yellow]No save files found automatically.[/yellow]")
            save_dir = self.config_manager.get_save_directory()
            if save_dir:
                self.console.print(f"[dim]Checked: {save_dir}[/dim]")

            return self.console.input("\nEnter save file path: ").strip()

    def _load_game_data(self, force_reload: bool = False):
        """Try to load game data for accurate production rates."""
        game_dir = self.config_manager.get_game_directory()

        if not game_dir:
            self.console.print("[dim]Game directory not found - using estimated rates[/dim]")
            return

        try:
            from .game_data import WaresExtractor

            cache_dir = self.config_manager.config.cache_directory
            self._wares_extractor = WaresExtractor(game_dir, cache_dir)

            if force_reload:
                self.console.print("[cyan]Extracting game data from game files...[/cyan]")
                self._wares_extractor.extract(force_reload=True)
            else:
                self.console.print("[cyan]Loading game data...[/cyan]")
                self._wares_extractor.extract()

            if self.analyzer.load_game_data(self._wares_extractor):
                self.console.print("[green]Loaded production rate data[/green]")
            else:
                self.console.print("[dim]Could not load game production data[/dim]")

        except Exception as e:
            self.console.print(f"[dim]Game data unavailable: {e}[/dim]")

    def _refresh_game_data(self):
        """Force refresh game data from game files."""
        self._load_game_data(force_reload=True)

    def run(self):
        """Run the main application loop."""
        self._show_banner()

        # Initial load
        if not self.load_save_file():
            return

        # Main menu loop
        while True:
            self.dashboard.display()
            self.dashboard.display_menu()

            choice = self.dashboard.prompt_choice()

            if choice == 'c':
                self.views.capacity_planning_view()
            elif choice == 's':
                self.views.station_view()
            elif choice == 'l':
                self.views.logistics_analysis_view()
            elif choice == 'p':
                self.views.search_production_view()
            elif choice == 'e':
                self.views.export_report_view()
            elif choice == 'n':
                if self.load_save_file():
                    continue
            elif choice == 'o':
                result = self.views.options_view(
                    refresh_game_data_callback=self._refresh_game_data,
                    reload_save_callback=lambda: True
                )
                if result == "reload_save":
                    if self.load_save_file(self._current_save_path):
                        continue
            elif choice in ('q', 'quit', 'exit'):
                self.console.print("\n[cyan]Thanks for using X4 Production Analyzer![/cyan]")
                break
            else:
                self.console.print("[red]Invalid choice[/red]")
                self.console.input("Press Enter to continue...")

    def _show_banner(self):
        """Show application banner."""
        banner = """╔═══════════════════════════════════════════════════════╗
║                                                       ║
║     X4 EMPIRE PRODUCTION ANALYZER v1.0                ║
║                                                       ║
║     Analyze your production empire and optimize      ║
║     resource management in X4: Foundations            ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝"""
        self.console.print(banner, style="bold cyan")
        self.console.print()


def main():
    """Main entry point."""
    app = X4Analyzer()
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
