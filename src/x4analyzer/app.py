"""Main application entry point."""

import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table

from .parsers.save_parser import SaveFileParser
from .parsers.data_extractor import DataExtractor
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

    def load_save_file(self, file_path: str = None):
        """Load and parse a save file."""
        # Try to find save file if not provided
        if not file_path:
            file_path = self._select_save_file()

        if not file_path:
            self.console.print("[red]No file specified[/red]")
            return False

        try:
            # Parse save file
            parser = SaveFileParser(file_path)
            self.console.print()
            root = parser.parse_with_progress()

            # Extract data
            extractor = DataExtractor(root)

            def progress_callback(msg, count):
                self.console.print(f"[cyan]{msg}[/cyan]")

            self.empire = extractor.extract_all(progress_callback)

            # Analyze
            self.console.print("[cyan]Analyzing production data...[/cyan]")
            self.analyzer = ProductionAnalyzer(self.empire)

            # Setup UI
            self.dashboard = Dashboard(self.empire, self.analyzer)
            self.views = ViewRenderer(self.empire, self.analyzer)

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

            if choice == '1':
                self.views.capacity_planning_view()
            elif choice == '2':
                self.views.station_view()
            elif choice == '3':
                self.views.logistics_analysis_view()
            elif choice == '4':
                self.views.search_production_view()
            elif choice == '5':
                self.views.export_report_view()
            elif choice == '6':
                if self.load_save_file():
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
