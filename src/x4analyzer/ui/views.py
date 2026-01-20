"""UI views for different menu options."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
import json
import csv
from pathlib import Path
from typing import Optional

from ..models.entities import EmpireData, Station
from ..analyzers.production_analyzer import ProductionAnalyzer, ProductionStats


class ViewRenderer:
    """Renders different view screens."""

    def __init__(self, empire: EmpireData, analyzer: ProductionAnalyzer):
        self.empire = empire
        self.analyzer = analyzer
        self.console = Console()

    def capacity_planning_view(self):
        """Display capacity planning analysis."""
        self.console.clear()
        self.console.print("[bold cyan]CAPACITY PLANNING[/bold cyan]\n")

        # Get user input
        query = self.console.input("Enter ware name to analyze: ").strip()

        if not query:
            return

        stats = self.analyzer.get_ware_stats(query)

        if not stats:
            self.console.print(f"[red]No production found for '{query}'[/red]")
            self._wait_for_enter()
            return

        # Display current production
        self.console.print(f"\n[bold]Production: {stats.ware.name}[/bold]")
        self.console.print(f"  Current modules: [green]{stats.module_count}[/green]")
        self.console.print(f"  Total stock: {stats.total_stock:,}")
        self.console.print(f"  Total capacity: {stats.total_capacity:,}")
        self.console.print(f"  Utilization: {stats.capacity_percent:.1f}%\n")

        # Analyze dependencies
        deps = self.analyzer.analyze_dependencies(query)

        # Display input requirements
        if deps["inputs"]:
            self.console.print("[bold yellow]Input Requirements:[/bold yellow]")
            table = Table(show_header=True, box=None)
            table.add_column("Input Ware", style="cyan")
            table.add_column("Modules", justify="right", style="green")
            table.add_column("Capacity", justify="right")

            for input_stats in deps["inputs"]:
                table.add_row(
                    input_stats.ware.name,
                    str(input_stats.module_count),
                    f"{input_stats.capacity_percent:.1f}%"
                )

            self.console.print(table)
            self.console.print()

            # Check for bottlenecks
            bottlenecks = [s for s in deps["inputs"] if s.capacity_percent < 50]
            if bottlenecks:
                self.console.print("[bold red]Bottleneck Warnings:[/bold red]")
                for bn in bottlenecks:
                    self.console.print(
                        f"  - {bn.ware.name}: Low capacity ({bn.capacity_percent:.1f}%)"
                    )
                self.console.print()

        # Display consumers
        if deps["consumers"]:
            self.console.print(f"[bold yellow]Used By:[/bold yellow]")
            for consumer in deps["consumers"]:
                self.console.print(f"  - {consumer.ware.name}")
            self.console.print()

        # Recommendations
        if deps["inputs"]:
            low_inputs = [s for s in deps["inputs"] if s.capacity_percent < 70]
            if low_inputs:
                self.console.print("[bold green]Recommended Expansions:[/bold green]")
                for inp in low_inputs:
                    self.console.print(f"  - Expand {inp.ware.name} production")
                self.console.print()

        self._wait_for_enter()

    def station_view(self):
        """Display station details."""
        self.console.clear()
        self.console.print("[bold cyan]STATION VIEW[/bold cyan]\n")

        # List all stations
        self.console.print("[bold]Your Stations:[/bold]")
        for i, station in enumerate(self.empire.stations, 1):
            products = len(station.unique_products)
            modules = len(station.production_modules)
            self.console.print(
                f"  [{i}] {station.name} - "
                f"[green]{modules} modules[/green], "
                f"[yellow]{products} products[/yellow]"
            )

        self.console.print()
        choice = self.console.input("Enter station number (or press Enter to cancel): ").strip()

        if not choice or not choice.isdigit():
            return

        idx = int(choice) - 1
        if idx < 0 or idx >= len(self.empire.stations):
            self.console.print("[red]Invalid selection[/red]")
            self._wait_for_enter()
            return

        self._display_station_details(self.empire.stations[idx])

    def _display_station_details(self, station: Station):
        """Display detailed information about a station."""
        self.console.clear()
        self.console.print(f"[bold cyan]{station.name}[/bold cyan]")
        self.console.print(f"Sector: {station.sector}")
        self.console.print(f"Total Modules: {len(station.production_modules)}\n")

        # Production table
        if station.production_modules:
            self.console.print("[bold]Production:[/bold]")
            table = Table(show_header=True, box=None)
            table.add_column("Product", style="cyan")
            table.add_column("Modules", justify="right", style="green")
            table.add_column("Stock", justify="right")
            table.add_column("Capacity", justify="right")

            # Group by product
            products = {}
            for module in station.production_modules:
                if module.output_ware:
                    if module.output_ware not in products:
                        products[module.output_ware] = {"count": 0, "stock": 0, "capacity": 0}
                    products[module.output_ware]["count"] += 1
                    if module.output:
                        products[module.output_ware]["stock"] += module.output.amount
                        products[module.output_ware]["capacity"] += module.output.capacity

            for ware, data in products.items():
                table.add_row(
                    ware.name,
                    str(data["count"]),
                    f"{data['stock']:,}",
                    f"{data['capacity']:,}"
                )

            self.console.print(table)
            self.console.print()

        # Ships
        if station.assigned_ships:
            self.console.print(f"[bold]Assigned Ships: {len(station.assigned_ships)}[/bold]")
            self.console.print(f"  Traders: [green]{len(station.traders)}[/green]")
            self.console.print(f"  Miners: [green]{len(station.miners)}[/green]")
            self.console.print(f"  Total Cargo: {station.total_cargo_capacity:,}\n")

        self._wait_for_enter()

    def logistics_analysis_view(self):
        """Display logistics analysis."""
        self.console.clear()
        self.console.print("[bold cyan]LOGISTICS ANALYSIS[/bold cyan]\n")

        summary = self.analyzer.get_logistics_summary()

        # Empire-wide summary
        self.console.print("[bold]Empire-Wide Summary:[/bold]")
        self.console.print(f"  Total Ships: [green]{summary['total_ships']}[/green]")
        self.console.print(f"  Traders: [cyan]{summary['traders']}[/cyan]")
        self.console.print(f"  Miners: [cyan]{summary['miners']}[/cyan]")
        self.console.print(f"  Total Cargo Capacity: {summary['total_cargo_capacity']:,}\n")

        # Per-station breakdown
        self.console.print("[bold]Station Assignments:[/bold]")
        table = Table(show_header=True, box=None)
        table.add_column("Station", style="cyan")
        table.add_column("Traders", justify="right", style="green")
        table.add_column("Miners", justify="right", style="green")
        table.add_column("Total Ships", justify="right")
        table.add_column("Cargo Capacity", justify="right")

        for station in self.empire.stations:
            if station.assigned_ships:
                table.add_row(
                    station.name,
                    str(len(station.traders)),
                    str(len(station.miners)),
                    str(len(station.assigned_ships)),
                    f"{station.total_cargo_capacity:,}"
                )

        self.console.print(table)
        self.console.print()

        # Identify stations with no ships
        no_ships = [s for s in self.empire.stations if not s.assigned_ships]
        if no_ships:
            self.console.print(f"[yellow]Stations with no assigned ships: {len(no_ships)}[/yellow]")
            for station in no_ships[:5]:
                self.console.print(f"  - {station.name}")
            if len(no_ships) > 5:
                self.console.print(f"  ... and {len(no_ships) - 5} more")
            self.console.print()

        self._wait_for_enter()

    def search_production_view(self):
        """Search for specific production."""
        self.console.clear()
        self.console.print("[bold cyan]SEARCH PRODUCTION[/bold cyan]\n")

        query = self.console.input("Enter search term: ").strip()

        if not query:
            return

        results = self.analyzer.search_production(query)

        if not results:
            self.console.print(f"[red]No results found for '{query}'[/red]")
            self._wait_for_enter()
            return

        self.console.print(f"\n[bold]Found {len(results)} result(s):[/bold]\n")

        table = Table(show_header=True, box=None)
        table.add_column("Ware", style="cyan")
        table.add_column("Category", style="yellow")
        table.add_column("Modules", justify="right", style="green")
        table.add_column("Stock", justify="right")
        table.add_column("Capacity %", justify="right")

        for stats in results:
            table.add_row(
                stats.ware.name,
                stats.ware.category.value,
                str(stats.module_count),
                f"{stats.total_stock:,}",
                f"{stats.capacity_percent:.1f}%"
            )

        self.console.print(table)
        self.console.print()
        self._wait_for_enter()

    def export_report_view(self):
        """Export data to file."""
        self.console.clear()
        self.console.print("[bold cyan]EXPORT REPORT[/bold cyan]\n")

        self.console.print("Select export format:")
        self.console.print("  [1] CSV")
        self.console.print("  [2] JSON")
        self.console.print()

        choice = self.console.input("Enter choice: ").strip()

        if choice == "1":
            self._export_csv()
        elif choice == "2":
            self._export_json()
        else:
            self.console.print("[red]Invalid choice[/red]")
            self._wait_for_enter()

    def _export_csv(self):
        """Export to CSV format."""
        filename = self.console.input("Enter filename (default: production_report.csv): ").strip()
        if not filename:
            filename = "production_report.csv"

        if not filename.endswith(".csv"):
            filename += ".csv"

        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Ware", "Category", "Modules", "Stock", "Capacity", "Utilization %"])

                for stats in self.analyzer.get_all_production_stats():
                    writer.writerow([
                        stats.ware.name,
                        stats.ware.category.value,
                        stats.module_count,
                        stats.total_stock,
                        stats.total_capacity,
                        f"{stats.capacity_percent:.2f}"
                    ])

            self.console.print(f"[green]Report exported to {filename}[/green]")
        except Exception as e:
            self.console.print(f"[red]Export failed: {e}[/red]")

        self._wait_for_enter()

    def _export_json(self):
        """Export to JSON format."""
        filename = self.console.input("Enter filename (default: production_report.json): ").strip()
        if not filename:
            filename = "production_report.json"

        if not filename.endswith(".json"):
            filename += ".json"

        try:
            data = {
                "empire": {
                    "player": self.empire.player_name,
                    "save_timestamp": self.empire.save_timestamp,
                    "total_stations": len(self.empire.stations),
                    "total_modules": self.empire.total_production_modules
                },
                "production": []
            }

            for stats in self.analyzer.get_all_production_stats():
                data["production"].append({
                    "ware_id": stats.ware.ware_id,
                    "ware_name": stats.ware.name,
                    "category": stats.ware.category.value,
                    "module_count": stats.module_count,
                    "total_stock": stats.total_stock,
                    "total_capacity": stats.total_capacity,
                    "capacity_percent": round(stats.capacity_percent, 2)
                })

            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)

            self.console.print(f"[green]Report exported to {filename}[/green]")
        except Exception as e:
            self.console.print(f"[red]Export failed: {e}[/red]")

        self._wait_for_enter()

    def _wait_for_enter(self):
        """Wait for user to press Enter."""
        self.console.input("\n[dim]Press Enter to continue...[/dim]")
