#!/usr/bin/env python3
"""
Azure Savings Report Generator
Main entry point for generating customer savings reports
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src import (
    create_data_source,
    SavingsCalculator,
    ReportGenerator,
    ADXDataSource
)

app = typer.Typer(
    name="azure-savings-report",
    help="Generate comprehensive Azure savings reports for customers"
)
console = Console()


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file"""
    config_file = Path(config_path)
    if not config_file.exists():
        console.print(f"[red]Config file not found: {config_path}[/red]")
        console.print("Please copy config.example.yaml to config.yaml and configure your settings.")
        raise typer.Exit(1)
    
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)


@app.command()
def generate(
    customer: Optional[str] = typer.Option(None, "--customer", "-c", help="Customer name for the report"),
    months: int = typer.Option(3, "--months", "-m", help="Number of months to analyze"),
    output_dir: Optional[str] = typer.Option(None, "--output", "-o", help="Output directory for reports"),
    config_path: str = typer.Option("config.yaml", "--config", help="Path to config file"),
    format: str = typer.Option("all", "--format", "-f", help="Output format: html, excel, or all")
):
    """Generate a savings report for a customer"""
    
    console.print("[bold blue]Azure Savings Realization Report Generator[/bold blue]")
    console.print("=" * 50)
    
    # Load configuration
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Loading configuration...", total=None)
        config = load_config(config_path)
    
    # Override config with CLI options
    if customer:
        config['report']['customer_name'] = customer
    if output_dir:
        config['report']['output_dir'] = output_dir
    if months:
        config['report']['months'] = months
    
    customer_name = config['report']['customer_name']
    output_directory = config['report']['output_dir']
    currency = config['report'].get('currency', 'USD')
    
    console.print(f"\n[green]Customer:[/green] {customer_name}")
    console.print(f"[green]Period:[/green] Last {months} months")
    console.print(f"[green]Output:[/green] {output_directory}")
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)
    
    # Connect to data source
    console.print("\n[bold]Connecting to data source...[/bold]")
    
    try:
        data_source = create_data_source(config)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task(description="Testing connection...", total=None)
            
            if not data_source.test_connection():
                console.print("[red]Failed to connect to data source[/red]")
                raise typer.Exit(1)
            
            progress.update(task, description="Connection successful!")
        
        console.print("[green]✓[/green] Connected to data source")
        
    except Exception as e:
        console.print(f"[red]Error connecting to data source: {e}[/red]")
        raise typer.Exit(1)
    
    # Fetch cost data
    console.print("\n[bold]Fetching cost data...[/bold]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task(description="Querying costs...", total=None)
        
        try:
            costs_df = data_source.get_costs(start_date, end_date)
            progress.update(task, description=f"Retrieved {len(costs_df):,} cost records")
        except Exception as e:
            console.print(f"[red]Error fetching costs: {e}[/red]")
            raise typer.Exit(1)
    
    if costs_df.empty:
        console.print("[yellow]Warning: No cost data found for the specified period[/yellow]")
        raise typer.Exit(1)
    
    console.print(f"[green]✓[/green] Retrieved {len(costs_df):,} cost records")
    
    # Fetch price data if available
    prices_df = None
    try:
        prices_df = data_source.get_prices()
        if not prices_df.empty:
            console.print(f"[green]✓[/green] Retrieved {len(prices_df):,} price records")
    except Exception:
        console.print("[yellow]Note: Price sheet data not available[/yellow]")
    
    # Calculate savings
    console.print("\n[bold]Calculating savings...[/bold]")
    
    calculator = SavingsCalculator(costs_df, prices_df)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task(description="Generating report...", total=None)
        report = calculator.generate_report(customer_name, start_date, end_date, currency)
    
    # Display summary
    console.print("\n[bold]Savings Summary[/bold]")
    
    summary_table = Table(show_header=True, header_style="bold blue")
    summary_table.add_column("Category", style="cyan")
    summary_table.add_column("Savings", justify="right", style="green")
    summary_table.add_column("% of Total", justify="right")
    
    categories = [
        ("Negotiated Discount", report.negotiated_discount_savings),
        ("Reserved Instances", report.reserved_instance_savings),
        ("Savings Plans", report.savings_plan_savings),
        ("Azure Hybrid Benefit", report.ahb_savings),
        ("Dev/Test Pricing", report.devtest_savings),
    ]
    
    for name, savings in categories:
        if savings.total_savings > 0:
            pct = (savings.total_savings / report.total_savings * 100) if report.total_savings > 0 else 0
            summary_table.add_row(
                name,
                f"${savings.total_savings:,.2f}",
                f"{pct:.1f}%"
            )
    
    summary_table.add_row("", "", "", style="dim")
    summary_table.add_row(
        "[bold]TOTAL SAVINGS[/bold]",
        f"[bold green]${report.total_savings:,.2f}[/bold green]",
        f"[bold]{report.total_savings_percentage:.1f}%[/bold]"
    )
    
    console.print(summary_table)
    
    # Generate reports
    console.print("\n[bold]Generating reports...[/bold]")
    
    generator = ReportGenerator(output_directory)
    generated_files = []
    
    if format in ('html', 'all'):
        html_path = generator.generate_html_report(report)
        generated_files.append(('HTML', html_path))
        console.print(f"[green]✓[/green] HTML report: {html_path}")
    
    if format in ('excel', 'all'):
        excel_path = generator.generate_excel_report(report)
        generated_files.append(('Excel', excel_path))
        console.print(f"[green]✓[/green] Excel report: {excel_path}")
    
    console.print("\n[bold green]Report generation complete![/bold green]")
    
    # Offer to open the HTML report
    if format in ('html', 'all'):
        if typer.confirm("\nWould you like to open the HTML report?"):
            import webbrowser
            webbrowser.open(f"file://{Path(html_path).absolute()}")


@app.command()
def test_connection(
    config_path: str = typer.Option("config.yaml", "--config", help="Path to config file")
):
    """Test the connection to the configured data source"""
    
    console.print("[bold]Testing data source connection...[/bold]")
    
    config = load_config(config_path)
    
    try:
        data_source = create_data_source(config)
        
        if data_source.test_connection():
            console.print("[green]✓ Connection successful![/green]")
            
            # Show data source info
            source_type = config['data_source']['type']
            console.print(f"  Data source type: {source_type}")
            
            if source_type == 'adx':
                console.print(f"  Cluster: {config['data_source']['adx']['cluster_uri']}")
                console.print(f"  Database: {config['data_source']['adx']['database']}")
            elif source_type == 'storage':
                console.print(f"  Storage account: {config['data_source']['storage']['account_name']}")
                console.print(f"  Container: {config['data_source']['storage']['container_name']}")
        else:
            console.print("[red]✗ Connection failed[/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def list_subscriptions(
    config_path: str = typer.Option("config.yaml", "--config", help="Path to config file"),
    months: int = typer.Option(1, "--months", "-m", help="Number of months to look back")
):
    """List subscriptions with cost data"""
    
    config = load_config(config_path)
    data_source = create_data_source(config)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)
    
    console.print(f"[bold]Fetching subscriptions for the last {months} month(s)...[/bold]")
    
    costs_df = data_source.get_costs(start_date, end_date)
    
    if costs_df.empty:
        console.print("[yellow]No cost data found[/yellow]")
        raise typer.Exit(1)
    
    # Group by subscription
    if 'SubAccountId' in costs_df.columns and 'SubAccountName' in costs_df.columns:
        subs = costs_df.groupby(['SubAccountId', 'SubAccountName']).agg({
            'EffectiveCost': 'sum'
        }).reset_index()
        
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Subscription Name")
        table.add_column("Subscription ID")
        table.add_column("Total Cost", justify="right")
        
        for _, row in subs.sort_values('EffectiveCost', ascending=False).iterrows():
            table.add_row(
                row['SubAccountName'],
                row['SubAccountId'],
                f"${row['EffectiveCost']:,.2f}"
            )
        
        console.print(table)
    else:
        console.print("[yellow]Subscription columns not found in data[/yellow]")


if __name__ == "__main__":
    app()
