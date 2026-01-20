"""Main application entry point."""

import sys
from pathlib import Path
from rich.console import Console

from .parsers.save_parser import SaveFileParser
from .parsers.data_extractor import DataExtractor
from .analyzers.production_analyzer import ProductionAnalyzer
from .ui.dashboard import Dashboard
from .ui.views import ViewRenderer


class X4Analyzer:
    """Main application class."""

    def __init__(self):
        self.console = Console()
        self.empire = None
        self.analyzer = None
        self.dashboard = None
        self.views = None

    def load_save_file(self, file_path: str = None):
        """Load and parse a save file."""
        # Try to find save file if not provided
        if not file_path:
            self.console.print("[cyan]Searching for X4 save file...[/cyan]")
            auto_path = SaveFileParser.find_default_save()

            if auto_path:
                self.console.print(f"[green]Found: {auto_path}[/green]")
                use_auto = self.console.input("Use this file? (Y/n): ").strip().lower()
                if use_auto != 'n':
                    file_path = str(auto_path)

            if not file_path:
                file_path = self.console.input("\nEnter save file path: ").strip()

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
        banner = """
╔═══════════════════════════════════════════════════════╗
║                                                       ║
║     X4 EMPIRE PRODUCTION ANALYZER v1.0                ║
║                                                       ║
║     Analyze your production empire and optimize      ║
║     resource management in X4: Foundations            ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
        """
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
