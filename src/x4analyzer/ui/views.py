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

        # Display current production with supply/demand
        self.console.print(f"\n[bold]Production: {stats.ware.name}[/bold]")
        self.console.print(f"  Production modules: [green]{stats.module_count}[/green]")
        self.console.print(f"  Current stock: {stats.total_stock:,}")
        self.console.print(f"  Storage capacity: {stats.total_capacity:,}")
        self.console.print()

        # Supply/Demand section
        self.console.print("[bold yellow]Supply vs Demand:[/bold yellow]")
        self.console.print(f"  Production output: {stats.total_production_output:,} (estimated capacity)")
        self.console.print(f"  Consumption demand: {stats.total_consumption_demand:,} (from internal stations)")

        # Color-code supply status
        status = stats.supply_status
        if status == "Shortage":
            self.console.print(f"  Supply status: [red]{status}[/red] ({stats.production_utilization:.0f}% demand/production)")
        elif status == "Surplus":
            self.console.print(f"  Supply status: [yellow]{status}[/yellow] ({stats.production_utilization:.0f}% demand/production)")
        elif status == "Balanced":
            self.console.print(f"  Supply status: [green]{status}[/green] ({stats.production_utilization:.0f}% demand/production)")
        else:
            self.console.print(f"  Supply status: [dim]{status}[/dim]")
        self.console.print()

        # Producing stations
        if stats.producing_stations:
            self.console.print("[bold yellow]Producing Stations:[/bold yellow]")
            for station_name, module_count in sorted(stats.producing_stations.items(), key=lambda x: -x[1]):
                self.console.print(f"  - {station_name}: [green]{module_count} modules[/green]")
            self.console.print()

        # Consuming stations
        if stats.consuming_stations:
            self.console.print("[bold yellow]Consuming Stations:[/bold yellow]")
            for station_name, demand in sorted(stats.consuming_stations.items(), key=lambda x: -x[1]):
                self.console.print(f"  - {station_name}: [cyan]{demand:,} demand[/cyan]")
            self.console.print()

        # Analyze dependencies
        deps = self.analyzer.analyze_dependencies(query)

        # Display input requirements
        if deps["inputs"]:
            self.console.print("[bold yellow]Input Requirements (for production):[/bold yellow]")
            table = Table(show_header=True, box=None)
            table.add_column("Input Ware", style="cyan")
            table.add_column("Modules", justify="right", style="green")
            table.add_column("Supply Status", justify="right")

            for input_stats in deps["inputs"]:
                status_color = "red" if input_stats.supply_status == "Shortage" else \
                               "yellow" if input_stats.supply_status == "Surplus" else \
                               "green" if input_stats.supply_status == "Balanced" else "dim"
                table.add_row(
                    input_stats.ware.name,
                    str(input_stats.module_count),
                    f"[{status_color}]{input_stats.supply_status}[/{status_color}]"
                )

            self.console.print(table)
            self.console.print()

            # Check for shortages in inputs
            shortages = [s for s in deps["inputs"] if s.supply_status == "Shortage"]
            if shortages:
                self.console.print("[bold red]Input Shortages:[/bold red]")
                for sh in shortages:
                    self.console.print(
                        f"  - {sh.ware.name}: [red]Demand at {sh.production_utilization:.0f}% of production[/red]"
                    )
                self.console.print()

        # Display what this ware is used to produce
        if deps["consumers"]:
            # Deduplicate consumers
            unique_consumers = {}
            for consumer in deps["consumers"]:
                if consumer.ware.ware_id not in unique_consumers:
                    unique_consumers[consumer.ware.ware_id] = consumer

            self.console.print(f"[bold yellow]Used To Produce:[/bold yellow]")
            for consumer in unique_consumers.values():
                self.console.print(f"  - {consumer.ware.name} ({consumer.module_count} modules)")
            self.console.print()

        # Recommendations
        if stats.supply_status == "Shortage":
            self.console.print("[bold red]RECOMMENDATION:[/bold red]")
            shortage_percent = stats.production_utilization - 100
            self.console.print(f"  Demand exceeds production by {shortage_percent:.0f}%")
            # Estimate modules needed
            if stats.module_count > 0:
                modules_needed = int(stats.module_count * (shortage_percent / 100)) + 1
                self.console.print(f"  Consider adding ~{modules_needed} more production modules")
            self.console.print()
        elif stats.supply_status == "Surplus" and stats.production_utilization < 50:
            self.console.print("[bold yellow]NOTE:[/bold yellow]")
            self.console.print(f"  Production significantly exceeds internal demand")
            self.console.print(f"  Excess may be sold to NPC factions for profit")
            self.console.print()

        self._wait_for_enter()

    def station_view(self):
        """Display station details."""
        self.console.clear()
        self.console.print("[bold cyan]STATION VIEW[/bold cyan]\n")

        # Sort stations by sector, then by name
        sorted_stations = sorted(self.empire.stations, key=lambda s: (s.sector, s.name))

        # List all stations grouped by sector
        self.console.print("[bold]Your Stations:[/bold]")
        current_sector = None
        for i, station in enumerate(sorted_stations, 1):
            # Print sector header when it changes
            if station.sector != current_sector:
                if current_sector is not None:
                    self.console.print()  # Blank line between sectors
                self.console.print(f"[yellow]{station.sector}:[/yellow]")
                current_sector = station.sector

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
        if idx < 0 or idx >= len(sorted_stations):
            self.console.print("[red]Invalid selection[/red]")
            self._wait_for_enter()
            return

        self._display_station_details(sorted_stations[idx])

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

        # Station type breakdown
        stations_by_type = self.analyzer.get_stations_by_type()
        self.console.print("[bold]Stations by Type:[/bold]")
        type_names = {
            "production": "Production Facilities",
            "wharf": "Wharfs",
            "shipyard": "Shipyards",
            "equipmentdock": "Equipment Docks",
            "defence": "Defence Platforms"
        }
        for station_type, stations in sorted(stations_by_type.items()):
            type_display = type_names.get(station_type, station_type.title())
            self.console.print(f"  {type_display}: [green]{len(stations)}[/green]")
        self.console.print()

        # Ship-building facilities consumption
        ship_builders = self.analyzer.get_ship_building_stations()
        if ship_builders:
            self.console.print("[bold yellow]Ship-Building Facility Consumption:[/bold yellow]")
            for station in ship_builders:
                self.console.print(f"  [cyan]{station.name}[/cyan] ({station.station_type})")
                if station.input_demands:
                    for ware_id, demand in sorted(station.input_demands.items(), key=lambda x: -x[1])[:5]:
                        from ..models.ware_database import get_ware
                        ware = get_ware(ware_id)
                        self.console.print(f"    - {ware.name}: {demand:,} demand")
                else:
                    self.console.print(f"    [dim]No active consumption data[/dim]")
            self.console.print()

        # Per-station breakdown
        self.console.print("[bold]Station Logistics Assignments:[/bold]")
        table = Table(show_header=True, box=None)
        table.add_column("Station", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Traders", justify="right", style="green")
        table.add_column("Miners", justify="right", style="green")
        table.add_column("Cargo", justify="right")

        for station in self.empire.stations:
            if station.assigned_ships:
                table.add_row(
                    station.name[:35] + "..." if len(station.name) > 38 else station.name,
                    station.station_type[:8],
                    str(len(station.traders)),
                    str(len(station.miners)),
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
        self.console.print("  [1] CSV (spreadsheet compatible)")
        self.console.print("  [2] JSON (for scripts/tools)")
        self.console.print("  [3] Text (human readable report)")
        self.console.print()

        choice = self.console.input("Enter choice: ").strip()

        if choice == "1":
            self._export_csv()
        elif choice == "2":
            self._export_json()
        elif choice == "3":
            self._export_text()
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
                writer.writerow([
                    "Ware", "Category", "Modules", "Stock", "Capacity",
                    "Stock %", "Production Output", "Consumption Demand",
                    "Supply/Demand %", "Supply Status"
                ])

                for stats in self.analyzer.get_all_production_stats():
                    writer.writerow([
                        stats.ware.name,
                        stats.ware.category.value,
                        stats.module_count,
                        stats.total_stock,
                        stats.total_capacity,
                        f"{stats.capacity_percent:.2f}",
                        stats.total_production_output,
                        stats.total_consumption_demand,
                        f"{stats.production_utilization:.2f}",
                        stats.supply_status
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
            # Logistics summary
            logistics = self.analyzer.get_logistics_summary()

            data = {
                "empire": {
                    "player": self.empire.player_name,
                    "save_timestamp": self.empire.save_timestamp,
                    "total_stations": len(self.empire.stations),
                    "total_modules": self.empire.total_production_modules,
                    "logistics": logistics
                },
                "production": [],
                "stations": []
            }

            for stats in self.analyzer.get_all_production_stats():
                data["production"].append({
                    "ware_id": stats.ware.ware_id,
                    "ware_name": stats.ware.name,
                    "category": stats.ware.category.value,
                    "module_count": stats.module_count,
                    "total_stock": stats.total_stock,
                    "total_capacity": stats.total_capacity,
                    "capacity_percent": round(stats.capacity_percent, 2),
                    "production_output": stats.total_production_output,
                    "consumption_demand": stats.total_consumption_demand,
                    "production_utilization": round(stats.production_utilization, 2),
                    "supply_status": stats.supply_status,
                    "producing_stations": stats.producing_stations,
                    "consuming_stations": stats.consuming_stations
                })

            for station in self.empire.stations:
                station_data = {
                    "station_id": station.station_id,
                    "name": station.name,
                    "sector": station.sector,
                    "station_type": station.station_type,
                    "production_modules": len(station.production_modules),
                    "products": [w.name for w in station.unique_products],
                    "assigned_ships": len(station.assigned_ships),
                    "traders": len(station.traders),
                    "miners": len(station.miners),
                    "cargo_capacity": station.total_cargo_capacity,
                    "input_demands": station.input_demands
                }
                data["stations"].append(station_data)

            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)

            self.console.print(f"[green]Report exported to {filename}[/green]")
        except Exception as e:
            self.console.print(f"[red]Export failed: {e}[/red]")

        self._wait_for_enter()

    def _export_text(self):
        """Export to human-readable text format."""
        filename = self.console.input("Enter filename (default: empire_report.txt): ").strip()
        if not filename:
            filename = "empire_report.txt"

        if not filename.endswith(".txt"):
            filename += ".txt"

        try:
            with open(filename, 'w') as f:
                # Header
                f.write("=" * 60 + "\n")
                f.write("X4 EMPIRE PRODUCTION REPORT\n")
                f.write("=" * 60 + "\n\n")

                f.write(f"Player: {self.empire.player_name}\n")
                f.write(f"Save Time: {self.empire.save_timestamp}\n")
                f.write(f"Total Stations: {len(self.empire.stations)}\n")
                f.write(f"Total Production Modules: {self.empire.total_production_modules}\n\n")

                # Production Summary
                f.write("-" * 60 + "\n")
                f.write("PRODUCTION SUMMARY\n")
                f.write("-" * 60 + "\n\n")

                from ..models.entities import WareCategory
                by_category = self.analyzer.get_production_by_category()

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

                    f.write(f"\n{category.value}:\n")
                    f.write("-" * 40 + "\n")
                    f.write(f"{'Ware':<25} {'Modules':>8} {'Stock':>10} {'Status':>12}\n")
                    f.write("-" * 40 + "\n")

                    for stats in by_category[category]:
                        f.write(f"{stats.ware.name:<25} {stats.module_count:>8} "
                               f"{stats.total_stock:>10,} {stats.supply_status:>12}\n")

                # Supply/Demand Analysis
                f.write("\n" + "-" * 60 + "\n")
                f.write("SUPPLY/DEMAND ANALYSIS\n")
                f.write("-" * 60 + "\n\n")

                shortages = self.analyzer.get_supply_shortages()
                if shortages:
                    f.write("SHORTAGES (demand > production):\n")
                    for stats in shortages:
                        f.write(f"  - {stats.ware.name}: {stats.production_utilization:.0f}% "
                               f"demand vs production\n")
                    f.write("\n")

                surplus = self.analyzer.get_supply_surplus()
                if surplus:
                    f.write("SURPLUS (production > demand):\n")
                    for stats in surplus[:10]:  # Top 10
                        f.write(f"  - {stats.ware.name}: {stats.production_utilization:.0f}% "
                               f"demand vs production\n")
                    f.write("\n")

                # Station List
                f.write("-" * 60 + "\n")
                f.write("STATION LIST\n")
                f.write("-" * 60 + "\n\n")

                for station in sorted(self.empire.stations, key=lambda s: s.name):
                    f.write(f"{station.name}\n")
                    f.write(f"  Type: {station.station_type}\n")
                    f.write(f"  Sector: {station.sector}\n")
                    f.write(f"  Production Modules: {len(station.production_modules)}\n")
                    f.write(f"  Assigned Ships: {len(station.assigned_ships)} "
                           f"({len(station.traders)} traders, {len(station.miners)} miners)\n")

                    if station.unique_products:
                        products = ", ".join(w.name for w in station.unique_products)
                        f.write(f"  Products: {products}\n")
                    f.write("\n")

                # Logistics Summary
                f.write("-" * 60 + "\n")
                f.write("LOGISTICS SUMMARY\n")
                f.write("-" * 60 + "\n\n")

                summary = self.analyzer.get_logistics_summary()
                f.write(f"Total Ships: {summary['total_ships']}\n")
                f.write(f"Traders: {summary['traders']}\n")
                f.write(f"Miners: {summary['miners']}\n")
                f.write(f"Total Cargo Capacity: {summary['total_cargo_capacity']:,}\n\n")

                f.write("=" * 60 + "\n")
                f.write("END OF REPORT\n")
                f.write("=" * 60 + "\n")

            self.console.print(f"[green]Report exported to {filename}[/green]")
        except Exception as e:
            self.console.print(f"[red]Export failed: {e}[/red]")

        self._wait_for_enter()

    def _wait_for_enter(self):
        """Wait for user to press Enter."""
        self.console.input("\n[bold cyan]Press Enter to return to main menu...[/bold cyan]")
