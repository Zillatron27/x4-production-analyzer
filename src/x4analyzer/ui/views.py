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

    def __init__(self, empire: EmpireData, analyzer: ProductionAnalyzer,
                 config_manager=None, save_file_path: str = None):
        self.empire = empire
        self.analyzer = analyzer
        self.console = Console()
        self.config_manager = config_manager
        self.save_file_path = save_file_path

    def capacity_planning_view(self):
        """Display capacity planning analysis with ware list."""
        while True:
            self.console.clear()
            self.console.print("[bold cyan]CAPACITY PLANNING[/bold cyan]\n")

            # Get all production stats grouped by category
            from ..models.entities import WareCategory
            by_category = self.analyzer.get_production_by_category()

            category_order = [
                WareCategory.TIER_3,
                WareCategory.TIER_2,
                WareCategory.TIER_1,
                WareCategory.RAW,
                WareCategory.UNKNOWN
            ]

            # Build flat list for numbering
            all_stats = []
            for category in category_order:
                if category in by_category:
                    all_stats.extend(by_category[category])

            if not all_stats:
                self.console.print("[yellow]No production data available[/yellow]")
                self._wait_for_enter()
                return

            # Check if we have rate data
            has_rates = self.analyzer.has_rate_data

            # Display numbered table grouped by category
            self.console.print("[bold]Select a ware to analyze:[/bold]")
            if has_rates:
                self.console.print("[dim]Showing actual production/consumption rates from game data[/dim]\n")
            else:
                self.console.print("[dim]Game data not loaded - showing storage-based estimates[/dim]\n")

            idx = 1
            for category in category_order:
                if category not in by_category or not by_category[category]:
                    continue

                self.console.print(f"[yellow]{category.value}:[/yellow]")

                table = Table(show_header=True, box=None, padding=(0, 1))
                table.add_column("#", style="bold", justify="right", width=4)
                table.add_column("Ware", style="cyan", min_width=20)
                table.add_column("Modules", justify="right", style="green", width=8)
                if has_rates:
                    table.add_column("Prod/hr", justify="right", width=10)
                    table.add_column("Cons/hr", justify="right", width=10)
                    table.add_column("Net/hr", justify="right", width=10)
                else:
                    table.add_column("Stock", justify="right", width=10)
                table.add_column("Status", justify="left", width=10)

                for stats in by_category[category]:
                    # Color-code status
                    status = stats.supply_status
                    if status == "Shortage":
                        status_display = f"[red]{status}[/red]"
                    elif status == "Surplus":
                        status_display = f"[green]{status}[/green]"
                    elif status == "Balanced":
                        status_display = f"[yellow]{status}[/yellow]"
                    else:
                        status_display = f"[dim]{status}[/dim]"

                    if has_rates:
                        balance = stats.rate_balance
                        if balance > 0:
                            balance_display = f"[green]+{balance:,.0f}[/green]"
                        elif balance < 0:
                            balance_display = f"[red]{balance:,.0f}[/red]"
                        else:
                            balance_display = "[dim]0[/dim]"

                        table.add_row(
                            str(idx),
                            stats.ware.name,
                            str(stats.module_count),
                            f"{stats.production_rate_per_hour:,.0f}",
                            f"{stats.consumption_rate_per_hour:,.0f}",
                            balance_display,
                            status_display
                        )
                    else:
                        table.add_row(
                            str(idx),
                            stats.ware.name,
                            str(stats.module_count),
                            f"{stats.total_stock:,}",
                            status_display
                        )
                    idx += 1

                self.console.print(table)
                self.console.print()

            # Options
            self.console.print("[dim]Enter number to select ware, type to search, or B to go back[/dim]")
            choice = self.console.input("Selection: ").strip()

            if not choice or choice.lower() == 'b':
                return

            # Convert to lowercase for text search (but preserve case for number check)
            choice_lower = choice.lower()

            # Check if it's a number
            if choice.isdigit():
                num = int(choice)
                if 1 <= num <= len(all_stats):
                    self._display_ware_details(all_stats[num - 1])
                    # Loop back to this menu after viewing details
                    continue
                else:
                    self.console.print(f"[red]Invalid selection. Enter 1-{len(all_stats)}[/red]")
                    self._wait_for_enter()
                    continue

            # Text search
            results = self.analyzer.search_production(choice)

            if not results:
                self.console.print(f"[red]No results found for '{choice}'[/red]")
                self._wait_for_enter()
                continue

            if len(results) == 1:
                self._display_ware_details(results[0])
                continue

            # Multiple results - show filtered selection
            selected = self._display_search_results(results, choice)
            if selected:
                self._display_ware_details(selected)
            # Loop back to main list

    def station_view(self):
        """Display station details."""
        while True:
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
            self.console.print("[dim]Enter station number, or B to go back[/dim]")
            choice = self.console.input("Selection: ").strip().lower()

            if not choice or choice == 'b':
                return

            if not choice.isdigit():
                self.console.print("[red]Invalid selection[/red]")
                self._wait_for_enter()
                continue

            idx = int(choice) - 1
            if idx < 0 or idx >= len(sorted_stations):
                self.console.print("[red]Invalid selection[/red]")
                self._wait_for_enter()
                continue

            self._display_station_details(sorted_stations[idx])
            # Loop back to station list after viewing details

    def _display_station_details(self, station: Station):
        """Display detailed information about a station."""
        self.console.clear()
        self.console.print(f"[bold cyan]{station.name}[/bold cyan]")
        self.console.print(f"Sector: {station.sector}")
        self.console.print(f"Type: {station.station_type.title()}")
        self.console.print(f"Total Modules: {len(station.production_modules)}\n")

        # Check if we have rate data
        has_rates = self.analyzer.has_rate_data

        # Production table
        if station.production_modules:
            self.console.print("[bold]Production:[/bold]")
            table = Table(show_header=True, box=None)
            table.add_column("Product", style="cyan")
            table.add_column("Modules", justify="right", style="green")
            table.add_column("Stock", justify="right")
            table.add_column("Capacity", justify="right")
            if has_rates:
                table.add_column("Rate/hr", justify="right", style="yellow")

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
                row = [
                    ware.name,
                    str(data["count"]),
                    f"{data['stock']:,}",
                    f"{data['capacity']:,}"
                ]
                if has_rates:
                    stats = self.analyzer.get_ware_stats(ware.ware_id)
                    if stats:
                        rate = stats.get_station_production_rate(station.name)
                        row.append(f"{rate:,.0f}")
                    else:
                        row.append("-")
                table.add_row(*row)

            self.console.print(table)
            self.console.print()

        # Consumption table (inputs this station needs)
        if has_rates:
            station_rates = self.analyzer.get_station_rates(station.name)
            consumption = station_rates.get("consumption", {})

            if consumption:
                self.console.print("[bold]Consumption (inputs needed):[/bold]")
                table = Table(show_header=True, box=None)
                table.add_column("Input Ware", style="cyan")
                table.add_column("Rate/hr", justify="right", style="yellow")
                table.add_column("Empire Status", justify="right")

                for ware_name, rate in sorted(consumption.items(), key=lambda x: -x[1]):
                    # Get empire-wide status for this ware
                    stats = None
                    for s in self.analyzer.get_all_production_stats():
                        if s.ware.name == ware_name:
                            stats = s
                            break

                    status = "-"
                    if stats:
                        status_text = stats.supply_status
                        if status_text == "Shortage":
                            status = f"[red]{status_text}[/red]"
                        elif status_text == "Surplus":
                            status = f"[green]{status_text}[/green]"
                        elif status_text == "Balanced":
                            status = f"[yellow]{status_text}[/yellow]"
                        else:
                            status = f"[dim]{status_text}[/dim]"

                    table.add_row(ware_name, f"{rate:,.0f}", status)

                self.console.print(table)
                self.console.print()

        # Net balance for this station (if rate data available)
        if has_rates:
            summary = self.analyzer.get_station_summary(station)
            net_rates = summary.get("net_rates", [])

            if net_rates:
                # Show wares that are net negative (station consumes more than produces)
                deficits = [n for n in net_rates if n["net_rate"] < 0]
                surpluses = [n for n in net_rates if n["net_rate"] > 0]

                if deficits:
                    self.console.print("[bold yellow]Net Deficits (needs import):[/bold yellow]")
                    for item in deficits[:5]:  # Top 5
                        self.console.print(
                            f"  {item['ware']}: [red]{item['net_rate']:+,.0f}/hr[/red] "
                            f"(consumes {item['consumption']:,.0f}, produces {item['production']:,.0f})"
                        )
                    if len(deficits) > 5:
                        self.console.print(f"  [dim]...and {len(deficits) - 5} more[/dim]")
                    self.console.print()

                if surpluses:
                    self.console.print("[bold green]Net Surplus (for export/storage):[/bold green]")
                    for item in surpluses[:5]:  # Top 5
                        self.console.print(
                            f"  {item['ware']}: [green]{item['net_rate']:+,.0f}/hr[/green]"
                        )
                    if len(surpluses) > 5:
                        self.console.print(f"  [dim]...and {len(surpluses) - 5} more[/dim]")
                    self.console.print()

        # Ships
        if station.assigned_ships:
            self.console.print(f"[bold]Assigned Ships: {len(station.assigned_ships)}[/bold]")
            self.console.print(f"  Traders: [green]{len(station.traders)}[/green]")

            miners = station.miners
            if miners:
                miner_cargo = sum(m.cargo_capacity for m in miners)
                self.console.print(f"  Miners: [green]{len(miners)}[/green] (cargo capacity: {miner_cargo:,})")

                # Show breakdown by cargo type
                solid_miners = [m for m in miners if "solid" in m.cargo_tags.lower()]
                liquid_miners = [m for m in miners if "liquid" in m.cargo_tags.lower()]
                if solid_miners:
                    solid_cargo = sum(m.cargo_capacity for m in solid_miners)
                    self.console.print(f"    Solid miners: {len(solid_miners)} ({solid_cargo:,} cargo)")
                if liquid_miners:
                    liquid_cargo = sum(m.cargo_capacity for m in liquid_miners)
                    self.console.print(f"    Liquid/Gas miners: {len(liquid_miners)} ({liquid_cargo:,} cargo)")
            else:
                self.console.print(f"  Miners: [green]0[/green]")

            self.console.print(f"  Total Cargo: {station.total_cargo_capacity:,}\n")

        self._wait_for_enter("station list")

    def logistics_analysis_view(self):
        """Display logistics analysis."""
        self.console.clear()
        self.console.print("[bold cyan]LOGISTICS ANALYSIS[/bold cyan]\n")

        summary = self.analyzer.get_logistics_summary()

        # Empire-wide summary
        self.console.print("[bold]Empire-Wide Summary:[/bold]")
        self.console.print(f"  Total Ships: [green]{summary['total_ships']}[/green] "
                          f"([cyan]{summary['assigned_ships']}[/cyan] assigned, "
                          f"[yellow]{summary['unassigned_ships']}[/yellow] unassigned)")
        self.console.print(f"  Traders: [cyan]{summary['traders']}[/cyan] "
                          f"({summary['assigned_traders']} assigned, {summary['unassigned_traders']} unassigned)")
        self.console.print(f"  Miners: [cyan]{summary['miners']}[/cyan] "
                          f"({summary['assigned_miners']} assigned, {summary['unassigned_miners']} unassigned)")
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

        # Display unassigned ships
        if self.empire.unassigned_ships:
            self.console.print(f"[bold yellow]Unassigned Ships: {len(self.empire.unassigned_ships)}[/bold yellow]")

            # Group by ship type
            unassigned_by_type = {}
            for ship in self.empire.unassigned_ships:
                ship_type = ship.ship_type
                if ship_type not in unassigned_by_type:
                    unassigned_by_type[ship_type] = []
                unassigned_by_type[ship_type].append(ship)

            table = Table(show_header=True, box=None)
            table.add_column("Type", style="cyan")
            table.add_column("Count", justify="right", style="green")
            table.add_column("Cargo", justify="right")
            table.add_column("Example Ships", style="dim")

            for ship_type, ships in sorted(unassigned_by_type.items(), key=lambda x: -len(x[1])):
                total_cargo = sum(s.cargo_capacity for s in ships)
                # Show first 3 ship names as examples
                examples = ", ".join(s.name for s in ships[:3])
                if len(ships) > 3:
                    examples += f" (+{len(ships) - 3} more)"

                table.add_row(
                    ship_type.title(),
                    str(len(ships)),
                    f"{total_cargo:,}",
                    examples[:50] + "..." if len(examples) > 50 else examples
                )

            self.console.print(table)
            self.console.print()

        self._wait_for_enter()

    def search_production_view(self):
        """Search for specific production - delegates to capacity planning view."""
        # Both views now show the same ware list with search capability
        self.capacity_planning_view()

    def _display_search_results(self, results, query: str) -> Optional[ProductionStats]:
        """Display search results and return selected stats or None."""
        self.console.clear()
        self.console.print(f"[bold]Found {len(results)} result(s) for '{query}':[/bold]\n")

        table = Table(show_header=True, box=None)
        table.add_column("#", style="bold", justify="right", width=4)
        table.add_column("Ware", style="cyan")
        table.add_column("Category", style="yellow")
        table.add_column("Modules", justify="right", style="green")
        table.add_column("Status", justify="left")

        for i, stats in enumerate(results, 1):
            status = stats.supply_status
            if status == "Shortage":
                status_display = f"[red]{status}[/red]"
            elif status == "Surplus":
                status_display = f"[green]{status}[/green]"
            elif status == "Balanced":
                status_display = f"[yellow]{status}[/yellow]"
            else:
                status_display = f"[dim]{status}[/dim]"

            table.add_row(
                str(i),
                stats.ware.name,
                stats.ware.category.value,
                str(stats.module_count),
                status_display
            )

        self.console.print(table)
        self.console.print()

        choice = self.console.input("Enter number to view details (or press Enter to go back): ").strip()

        if choice and choice.isdigit():
            num = int(choice)
            if 1 <= num <= len(results):
                return results[num - 1]

        return None

    def _display_ware_details(self, stats: ProductionStats):
        """Display detailed information about a ware's production."""
        self.console.clear()
        self.console.print(f"[bold cyan]Production: {stats.ware.name}[/bold cyan]")
        self.console.print(f"Category: {stats.ware.category.value}\n")

        # Basic stats
        self.console.print(f"  Production modules: [green]{stats.module_count}[/green]")
        self.console.print(f"  Current stock: {stats.total_stock:,}")
        self.console.print(f"  Storage capacity: {stats.total_capacity:,}")
        self.console.print()

        # Production/Consumption rates (if available)
        if stats.has_rate_data:
            self.console.print("[bold yellow]Production & Consumption Rates:[/bold yellow]")
            self.console.print(f"  Production: [green]{stats.production_rate_per_hour:,.0f}[/green] units/hour")
            self.console.print(f"  Consumption: [cyan]{stats.consumption_rate_per_hour:,.0f}[/cyan] units/hour")

            # Net balance
            balance = stats.rate_balance
            if balance > 0:
                self.console.print(f"  Net balance: [green]+{balance:,.0f}[/green] units/hour (surplus)")
            elif balance < 0:
                self.console.print(f"  Net balance: [red]{balance:,.0f}[/red] units/hour (deficit)")
            else:
                self.console.print(f"  Net balance: [yellow]0[/yellow] units/hour (balanced)")
            self.console.print()

        # Supply/Demand section (storage-based estimates)
        self.console.print("[bold yellow]Storage-Based Estimates:[/bold yellow]")
        self.console.print(f"  Production capacity: {stats.total_production_output:,} (storage estimate)")
        self.console.print(f"  Requested stock: {stats.total_consumption_demand:,} (buy orders)")
        if not stats.has_rate_data:
            self.console.print(f"  [dim]Note: Game data not loaded - using storage estimates[/dim]")

        # Color-code supply status
        status = stats.supply_status
        if status == "Shortage":
            self.console.print(f"  Supply status: [red]{status}[/red]")
        elif status == "Surplus":
            self.console.print(f"  Supply status: [green]{status}[/green]")
        elif status == "Balanced":
            self.console.print(f"  Supply status: [yellow]{status}[/yellow]")
        else:
            self.console.print(f"  Supply status: [dim]{status}[/dim]")
        self.console.print()

        # Producing stations
        if stats.producing_stations:
            self.console.print("[bold yellow]Producing Stations:[/bold yellow]")
            for station_name, module_count in sorted(stats.producing_stations.items(), key=lambda x: -x[1]):
                rate_str = ""
                if stats.has_rate_data and station_name in stats.station_production_rates:
                    rate = stats.station_production_rates[station_name]
                    rate_str = f" ([yellow]{rate:,.0f}/hr[/yellow])"
                self.console.print(f"  - {station_name}: [green]{module_count} modules[/green]{rate_str}")
            self.console.print()

        # Stations consuming this ware
        if stats.station_consumption_rates:
            self.console.print("[bold yellow]Consuming Stations:[/bold yellow]")
            for station_name, rate in sorted(stats.station_consumption_rates.items(), key=lambda x: -x[1]):
                self.console.print(f"  - {station_name}: [cyan]{rate:,.0f}/hr[/cyan]")
            self.console.print()
        elif stats.consuming_stations:
            # Fall back to storage-based if no rate data
            self.console.print("[bold yellow]Stations Requesting (storage-based):[/bold yellow]")
            for station_name, demand in sorted(stats.consuming_stations.items(), key=lambda x: -x[1]):
                self.console.print(f"  - {station_name}: [cyan]{demand:,} requested[/cyan]")
            self.console.print()

        # Analyze dependencies
        deps = self.analyzer.analyze_dependencies(stats.ware.ware_id)

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

        # Display what this ware is used to produce
        if deps["consumers"]:
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
            if stats.module_count > 0:
                modules_needed = int(stats.module_count * (shortage_percent / 100)) + 1
                self.console.print(f"  Consider adding ~{modules_needed} more production modules")
            self.console.print()
        elif stats.supply_status == "Surplus" and stats.production_utilization < 50:
            self.console.print("[bold yellow]NOTE:[/bold yellow]")
            self.console.print(f"  Production significantly exceeds internal demand")
            self.console.print(f"  Excess may be sold to NPC factions for profit")
            self.console.print()

        self._wait_for_enter("ware list")

    def export_report_view(self):
        """Export data to file."""
        self.console.clear()
        self.console.print("[bold cyan]EXPORT REPORT[/bold cyan]\n")

        self.console.print("Select export format:")
        self.console.print("  [C] CSV (spreadsheet compatible)")
        self.console.print("  [J] JSON (for scripts/tools)")
        self.console.print("  [T] Text (human readable report)")
        self.console.print("  [B] Back")
        self.console.print()

        choice = self.console.input("Enter choice: ").strip().lower()

        if choice == "c":
            self._export_csv()
        elif choice == "j":
            self._export_json()
        elif choice == "t":
            self._export_text()
        elif choice == "b":
            return
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

        has_rates = self.analyzer.has_rate_data

        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)

                # Header with rate columns if available
                header = [
                    "Ware", "Category", "Modules", "Stock", "Capacity", "Stock %"
                ]
                if has_rates:
                    header.extend([
                        "Production/hr", "Consumption/hr", "Net Rate/hr"
                    ])
                header.extend([
                    "Storage Estimate", "Storage Demand", "Supply Status"
                ])
                writer.writerow(header)

                for stats in self.analyzer.get_all_production_stats():
                    row = [
                        stats.ware.name,
                        stats.ware.category.value,
                        stats.module_count,
                        stats.total_stock,
                        stats.total_capacity,
                        f"{stats.capacity_percent:.2f}"
                    ]
                    if has_rates:
                        row.extend([
                            f"{stats.production_rate_per_hour:.0f}",
                            f"{stats.consumption_rate_per_hour:.0f}",
                            f"{stats.rate_balance:.0f}"
                        ])
                    row.extend([
                        stats.total_production_output,
                        stats.total_consumption_demand,
                        stats.supply_status
                    ])
                    writer.writerow(row)

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
                ware_data = {
                    "ware_id": stats.ware.ware_id,
                    "ware_name": stats.ware.name,
                    "category": stats.ware.category.value,
                    "module_count": stats.module_count,
                    "total_stock": stats.total_stock,
                    "total_capacity": stats.total_capacity,
                    "capacity_percent": round(stats.capacity_percent, 2),
                    "storage_estimate": stats.total_production_output,
                    "storage_demand": stats.total_consumption_demand,
                    "production_utilization": round(stats.production_utilization, 2),
                    "supply_status": stats.supply_status,
                    "producing_stations": stats.producing_stations,
                    "consuming_stations": stats.consuming_stations
                }

                # Add rate data if available
                if stats.has_rate_data:
                    ware_data.update({
                        "production_rate_per_hour": round(stats.production_rate_per_hour, 2),
                        "consumption_rate_per_hour": round(stats.consumption_rate_per_hour, 2),
                        "net_rate_per_hour": round(stats.rate_balance, 2),
                        "station_production_rates": stats.station_production_rates,
                        "station_consumption_rates": stats.station_consumption_rates
                    })

                data["production"].append(ware_data)

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
                    WareCategory.TIER_3,
                    WareCategory.TIER_2,
                    WareCategory.TIER_1,
                    WareCategory.RAW,
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

    def _wait_for_enter(self, message: str = "main menu"):
        """Wait for user to press Enter."""
        self.console.input(f"\n[bold cyan]Press Enter to return to {message}...[/bold cyan]")

    def options_view(self, refresh_game_data_callback=None, reload_save_callback=None):
        """Display options menu."""
        while True:
            self.console.clear()
            self.console.print("[bold cyan]OPTIONS[/bold cyan]\n")

            # Current save file info
            self.console.print("[bold]Current Save File:[/bold]")
            if self.save_file_path:
                save_path = Path(self.save_file_path)
                if save_path.exists():
                    stat = save_path.stat()
                    import time
                    modified = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))
                    size_mb = stat.st_size / (1024 * 1024)
                    self.console.print(f"  Path: [cyan]{self.save_file_path}[/cyan]")
                    self.console.print(f"  Size: {size_mb:.1f} MB")
                    self.console.print(f"  Modified: {modified}")
                else:
                    self.console.print(f"  [dim]{self.save_file_path}[/dim]")
            else:
                self.console.print("  [dim]No save file loaded[/dim]")

            # Empire info from save
            self.console.print(f"\n[bold]Empire Info:[/bold]")
            self.console.print(f"  Commander: [cyan]{self.empire.player_name}[/cyan]")
            self.console.print(f"  Save Timestamp: {self.empire.save_timestamp}")
            self.console.print(f"  Stations: {len(self.empire.stations)}")
            self.console.print(f"  Total Ships: {len(self.empire.all_ships)}")

            # Game data info
            self.console.print(f"\n[bold]Game Data:[/bold]")
            if self.config_manager:
                game_dir = self.config_manager.get_game_directory()
                if game_dir:
                    self.console.print(f"  Game Directory: [cyan]{game_dir}[/cyan]")
                else:
                    self.console.print("  Game Directory: [dim]Not found[/dim]")

                cache_dir = self.config_manager.config.cache_directory
                if cache_dir:
                    cache_path = Path(cache_dir) / "wares_cache.json"
                    if cache_path.exists():
                        stat = cache_path.stat()
                        import time
                        cached_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))
                        self.console.print(f"  Wares Cache: [green]Available[/green] (cached {cached_time})")
                    else:
                        self.console.print("  Wares Cache: [yellow]Not cached[/yellow]")
            else:
                self.console.print("  [dim]Config not available[/dim]")

            if self.analyzer.has_rate_data:
                self.console.print("  Production Rates: [green]Loaded[/green]")
            else:
                self.console.print("  Production Rates: [yellow]Using estimates[/yellow]")

            # Menu options
            self.console.print(f"\n[bold]Actions:[/bold]")
            self.console.print("  [G] Refresh Game Data  - Re-extract wares from game files")
            self.console.print("  [R] Reload Save File   - Re-parse the current save file")
            self.console.print("  [B] Back               - Return to main menu")
            self.console.print()

            choice = self.console.input("[bold]Enter choice: [/bold]").strip().lower()

            if choice == 'g':
                if refresh_game_data_callback:
                    self.console.print("\n[cyan]Refreshing game data...[/cyan]")
                    refresh_game_data_callback()
                    self.console.input("\n[bold]Press Enter to continue...[/bold]")
                else:
                    self.console.print("[yellow]Game data refresh not available[/yellow]")
                    self.console.input("\n[bold]Press Enter to continue...[/bold]")
            elif choice == 'r':
                if reload_save_callback:
                    self.console.print("\n[cyan]Reloading save file...[/cyan]")
                    return "reload_save"
                else:
                    self.console.print("[yellow]Save reload not available[/yellow]")
                    self.console.input("\n[bold]Press Enter to continue...[/bold]")
            elif choice in ('b', 'back', ''):
                return None
            else:
                self.console.print("[red]Invalid choice[/red]")
                self.console.input("\n[bold]Press Enter to continue...[/bold]")
