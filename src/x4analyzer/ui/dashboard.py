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

        # Define category display order (highest tier first)
        category_order = [
            WareCategory.TIER_3,
            WareCategory.TIER_2,
            WareCategory.TIER_1,
            WareCategory.RAW,
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

        # Check if we have rate data available
        has_rates = self.analyzer.has_rate_data

        # Create table with appropriate columns
        table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
        table.add_column("Ware", style="cyan")
        table.add_column("Modules", justify="right", style="green")
        if has_rates:
            table.add_column("Prod/hr", justify="right")
            table.add_column("Cons/hr", justify="right")
            table.add_column("Balance", justify="right")
        else:
            table.add_column("Stock", justify="right")
            table.add_column("Supply/Demand", justify="left")
        table.add_column("Status", justify="left")

        for stats in stats_list:
            # Color-code supply status
            status = stats.supply_status
            if status == "Shortage":
                status_display = f"[red]{status}[/red]"
            elif status == "Surplus":
                status_display = f"[yellow]{status}[/yellow]"
            elif status == "Balanced":
                status_display = f"[green]{status}[/green]"
            else:
                status_display = f"[dim]{status}[/dim]"

            if has_rates:
                # Show rate-based data
                prod_rate = stats.production_rate_per_hour
                cons_rate = stats.consumption_rate_per_hour
                balance = stats.rate_balance

                # Format production (0 for consumed-only wares like raw materials)
                if prod_rate > 0:
                    prod_display = f"{prod_rate:,.0f}"
                else:
                    prod_display = "[dim]0[/dim]"

                # Format consumption
                if cons_rate > 0:
                    cons_display = f"{cons_rate:,.0f}"
                else:
                    cons_display = "[dim]0[/dim]"

                # Format balance with color
                if balance > 0:
                    balance_display = f"[green]+{balance:,.0f}[/green]"
                elif balance < 0:
                    balance_display = f"[red]{balance:,.0f}[/red]"
                else:
                    balance_display = "[dim]0[/dim]"

                table.add_row(
                    stats.ware.name,
                    str(stats.module_count),
                    prod_display,
                    cons_display,
                    balance_display,
                    status_display
                )
            else:
                # Fallback to storage-based display
                utilization_bar = self._create_utilization_bar(stats.production_utilization)
                table.add_row(
                    stats.ware.name,
                    str(stats.module_count),
                    f"{stats.total_stock:,}",
                    utilization_bar,
                    status_display
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

    def _create_utilization_bar(self, percent: float, width: int = 15) -> str:
        """Create a text-based utilization bar (supply vs demand)."""
        if percent == 0:
            return "[dim]No Demand[/dim]"

        # Cap at 200% for display purposes
        display_percent = min(percent, 200)
        filled = int((display_percent / 200) * width)
        empty = width - filled

        # Color based on utilization level
        # Green = balanced (80-120%), Yellow = surplus (<80%), Red = shortage (>120%)
        if percent < 80:
            color = "yellow"  # Surplus - could sell excess
        elif percent <= 120:
            color = "green"   # Balanced - ideal
        else:
            color = "red"     # Shortage - need more production

        bar = f"[{color}]{'█' * filled}[/{color}]"
        bar += f"[dim]{'░' * empty}[/dim]"
        bar += f" {percent:.0f}%"

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

        # Supply shortages (high priority)
        shortages = self.analyzer.get_supply_shortages()
        if shortages:
            self.console.print(
                f"  [red]Supply Shortages:[/red] "
                f"{len(shortages)} wares with requests exceeding production"
            )
            for stats in shortages[:3]:
                self.console.print(
                    f"    - [red]{stats.ware.name}[/red] "
                    f"({stats.production_utilization:.0f}% requested vs capacity)"
                )

        # Low stock warnings (secondary)
        bottlenecks = self.analyzer.get_potential_bottlenecks(stock_threshold=30.0)
        # Filter out already shown shortages
        shortage_wares = {s.ware for s in shortages} if shortages else set()
        bottlenecks = [b for b in bottlenecks if b.ware not in shortage_wares]
        if bottlenecks:
            self.console.print(
                f"  [yellow]Low Stock:[/yellow] "
                f"{len(bottlenecks)} wares below 30% capacity"
            )
            for stats in bottlenecks[:2]:
                self.console.print(
                    f"    - [yellow]{stats.ware.name}[/yellow] "
                    f"({stats.capacity_percent:.1f}% storage)"
                )

        self.console.print()

    def display_menu(self):
        """Display the main menu."""
        menu_text = """
[bold cyan]MENU OPTIONS:[/bold cyan]

  [C] CAPACITY PLANNING   - Analyze production dependencies
  [S] STATION VIEW        - View individual station details
  [L] LOGISTICS ANALYSIS  - Trader/miner assignments
  [E] EXPORT REPORT       - Export data to CSV/JSON
  [N] LOAD NEW SAVE       - Load a different save file
  [O] OPTIONS             - Settings and refresh options
  [Q] QUIT                - Exit analyzer

"""
        self.console.print(menu_text)

    def prompt_choice(self) -> str:
        """Prompt user for menu choice."""
        choice = self.console.input("[bold]Enter choice: [/bold]").strip().lower()
        return choice
