"""Main dashboard UI using rich library."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.progress import BarColumn, Progress
from typing import List

from ..models.entities import EmpireData, WareCategory
from ..analyzers.production_analyzer import ProductionAnalyzer, ProductionStats


class Dashboard:
    """Main dashboard display."""

    def __init__(self, empire: EmpireData, analyzer: ProductionAnalyzer):
        self.empire = empire
        self.analyzer = analyzer
        self.console = Console()

    def display(self):
        """Display the main dashboard."""
        self.console.clear()
        self._display_header()
        self._display_production_overview()
        self._display_quick_stats()

    def _display_header(self):
        """Display dashboard header."""
        header_text = Text()
        header_text.append("X4 EMPIRE PRODUCTION ANALYZER\n", style="bold cyan")
        header_text.append(f"Save: {self.empire.save_timestamp}\n", style="dim")
        header_text.append(f"Player: {self.empire.player_name}\n", style="dim")
        header_text.append(
            f"Stations: {len(self.empire.stations)} | "
            f"Production Modules: {self.empire.total_production_modules}",
            style="bold green"
        )

        panel = Panel(header_text, border_style="cyan", padding=(1, 2))
        self.console.print(panel)
        self.console.print()

    def _display_production_overview(self):
        """Display production overview grouped by category."""
        self.console.print("[bold]PRODUCTION OVERVIEW[/bold]")
        self.console.print()

        by_category = self.analyzer.get_production_by_category()

        # Define category display order
        category_order = [
            WareCategory.SHIP_COMPONENTS,
            WareCategory.ADVANCED_MATERIALS,
            WareCategory.INTERMEDIATE,
            WareCategory.BASIC,
            WareCategory.UNKNOWN
        ]

        for category in category_order:
            if category not in by_category or not by_category[category]:
                continue

            self._display_category(category, by_category[category])
            self.console.print()

    def _display_category(self, category: WareCategory, stats_list: List[ProductionStats]):
        """Display a single category of production."""
        # Category header
        self.console.print(f"  [bold yellow]{category.value}[/bold yellow]")

        # Create table
        table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
        table.add_column("Ware", style="cyan")
        table.add_column("Modules", justify="right", style="green")
        table.add_column("Stock", justify="right")
        table.add_column("Capacity", justify="right")
        table.add_column("Utilization", justify="left")

        for stats in stats_list:
            # Create capacity bar
            capacity_bar = self._create_capacity_bar(stats.capacity_percent)

            table.add_row(
                stats.ware.name,
                str(stats.module_count),
                f"{stats.total_stock:,}",
                f"{stats.total_capacity:,}",
                capacity_bar
            )

        self.console.print(table)

    def _create_capacity_bar(self, percent: float, width: int = 20) -> str:
        """Create a text-based capacity bar."""
        if percent == 0:
            return "[dim]N/A[/dim]"

        filled = int((percent / 100) * width)
        empty = width - filled

        # Color based on capacity level
        if percent < 30:
            color = "red"
        elif percent < 70:
            color = "yellow"
        else:
            color = "green"

        bar = f"[{color}]{'█' * filled}[/{color}]"
        bar += f"[dim]{'░' * empty}[/dim]"
        bar += f" {percent:.1f}%"

        return bar

    def _display_quick_stats(self):
        """Display quick statistics section."""
        self.console.print("[bold]QUICK STATS[/bold]")

        # Most produced ware
        top_produced = self.analyzer.get_most_produced(1)
        if top_produced:
            stats = top_produced[0]
            self.console.print(
                f"  Most Produced: [cyan]{stats.ware.name}[/cyan] "
                f"([green]{stats.module_count} modules[/green])"
            )

        # Multi-product stations
        diverse = self.analyzer.get_diverse_stations(min_products=3)
        if diverse:
            station = diverse[0]
            self.console.print(
                f"  Most Diverse Station: [cyan]{station.name}[/cyan] "
                f"([green]{len(station.unique_products)} products[/green])"
            )

        # Potential bottlenecks
        bottlenecks = self.analyzer.get_potential_bottlenecks(stock_threshold=30.0)
        if bottlenecks:
            self.console.print(
                f"  [yellow]Potential Bottlenecks:[/yellow] "
                f"{len(bottlenecks)} wares with low stock"
            )
            for stats in bottlenecks[:3]:
                self.console.print(
                    f"    - [red]{stats.ware.name}[/red] "
                    f"({stats.capacity_percent:.1f}% capacity)"
                )

        self.console.print()

    def display_menu(self):
        """Display the main menu."""
        menu_text = """
[bold cyan]MENU OPTIONS:[/bold cyan]

  [1] CAPACITY PLANNING   - Analyze production dependencies
  [2] STATION VIEW        - View individual station details
  [3] LOGISTICS ANALYSIS  - Trader/miner assignments
  [4] SEARCH PRODUCTION   - Search for specific wares
  [5] EXPORT REPORT       - Export data to CSV/JSON
  [6] LOAD NEW SAVE       - Load a different save file
  [Q] QUIT                - Exit analyzer

"""
        self.console.print(menu_text)

    def prompt_choice(self) -> str:
        """Prompt user for menu choice."""
        choice = self.console.input("[bold]Enter choice: [/bold]").strip().lower()
        return choice
