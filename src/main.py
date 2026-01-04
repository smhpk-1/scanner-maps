#!/usr/bin/env python3
"""
Google Places API Scanner - Main entry point.

Scans GitHub for exposed Google Places API Keys.
"""

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from tqdm import tqdm

from database import Database
from scanner import GitHubScanner
from validator import PlacesAPIValidator

console = Console()


def print_banner():
    """Print the application banner."""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║         🗺️  Google Places API Scanner  🗺️                      ║
║                                                               ║
║  Scan GitHub for exposed Google Places API Keys              ║
║  For security research purposes only!                        ║
╚═══════════════════════════════════════════════════════════════╝
    """
    console.print(Panel(banner, style="bold blue"))


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Scan GitHub for exposed Google Places API Keys"
    )
    
    parser.add_argument(
        "--from-iter",
        type=int,
        default=0,
        help="Start scanning from a specific iteration"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    
    parser.add_argument(
        "-ceko", "--check-existed-keys-only",
        action="store_true",
        help="Only validate existing keys in database"
    )
    
    parser.add_argument(
        "-k", "--keywords",
        nargs="+",
        help="Custom search keywords"
    )
    
    parser.add_argument(
        "-l", "--languages",
        nargs="+",
        help="Limit search to specific programming languages"
    )
    
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (no GUI)"
    )
    
    parser.add_argument(
        "--max-pages",
        type=int,
        default=5,
        help="Maximum pages to scan per keyword/language combo"
    )
    
    parser.add_argument(
        "--db",
        type=str,
        default="google_places.db",
        help="Path to SQLite database file"
    )
    
    parser.add_argument(
        "--high-value",
        action="store_true",
        help="Also scan high-value file types (.bash_history, AndroidManifest, .ipynb, etc.)"
    )
    
    parser.add_argument(
        "--high-value-only",
        action="store_true",
        help="Only scan high-value file types (skip keyword/language search)"
    )
    
    return parser.parse_args()


def validate_keys(db: Database, validator: PlacesAPIValidator):
    """Validate all unchecked keys in the database."""
    unchecked = db.get_unchecked_keys()
    
    if not unchecked:
        console.print("[yellow]No unchecked keys found in database.[/yellow]")
        return
    
    console.print(f"\n[bold]Validating {len(unchecked)} API keys...[/bold]\n")
    
    valid_count = 0
    invalid_count = 0
    
    for key_id, api_key, source_url in tqdm(unchecked, desc="Validating keys"):
        status, error_msg = validator.validate_key(api_key)
        db.update_key_status(api_key, status, error_msg)
        
        if status == "valid":
            valid_count += 1
            console.print(f"[bold green]✓ Valid key found: {api_key[:20]}...[/bold green]")
        else:
            invalid_count += 1
            if error_msg:
                console.print(f"[dim]✗ {api_key[:20]}... - {status}: {error_msg}[/dim]")
        
        # Rate limiting for API calls
        import time
        time.sleep(0.5)
    
    console.print(f"\n[bold]Validation complete![/bold]")
    console.print(f"[green]Valid: {valid_count}[/green] | [red]Invalid: {invalid_count}[/red]")


def display_summary(db: Database):
    """Display a summary of all keys in the database."""
    counts = db.get_key_count()
    
    if not counts:
        console.print("[yellow]No keys in database yet.[/yellow]")
        return
    
    table = Table(title="API Key Summary")
    table.add_column("Status", style="cyan")
    table.add_column("Count", style="magenta")
    
    for status, count in sorted(counts.items()):
        style = "green" if status == "valid" else "red" if status == "invalid" else "yellow"
        table.add_row(status, f"[{style}]{count}[/]")
    
    console.print(table)


def display_valid_keys(db: Database):
    """Display all valid keys."""
    valid_keys = db.get_valid_keys()
    
    if not valid_keys:
        console.print("[yellow]No valid keys found.[/yellow]")
        return
    
    table = Table(title="Valid API Keys")
    table.add_column("ID", style="dim")
    table.add_column("API Key", style="green")
    table.add_column("Source URL", style="blue")
    
    for key_id, api_key, source_url in valid_keys:
        table.add_row(
            str(key_id),
            f"{api_key[:30]}...",
            source_url[:50] + "..." if source_url and len(source_url) > 50 else source_url or "N/A"
        )
    
    console.print(table)


def main():
    """Main entry point."""
    print_banner()
    args = parse_args()
    
    # Initialize database
    db = Database(args.db)
    validator = PlacesAPIValidator()
    
    console.print(f"[dim]Database: {args.db}[/dim]\n")
    
    # Show current summary
    display_summary(db)
    
    if args.check_existed_keys_only:
        # Only validate existing keys
        console.print("\n[bold]Mode: Check existing keys only[/bold]")
        validate_keys(db, validator)
        display_valid_keys(db)
        db.close()
        return
    
    # Start scanning
    try:
        scanner = GitHubScanner(headless=args.headless, debug=args.debug)
        scanner.start()
        
        if not scanner.logged_in:
            console.print("[bold red]Failed to log in to GitHub. Exiting.[/bold red]")
            scanner.close()
            db.close()
            sys.exit(1)
        
        results = []
        new_keys = 0
        
        # Perform standard keyword/language search
        if not args.high_value_only:
            console.print("\n[bold cyan]Phase 1: Keyword-based search[/bold cyan]")
            keyword_results = scanner.search(
                keywords=args.keywords,
                languages=args.languages,
                from_iter=args.from_iter,
                max_pages=args.max_pages
            )
            results.extend(keyword_results)
            console.print(f"[green]Found {len(keyword_results)} keys from keyword search[/green]")
        
        # Perform high-value path-based search
        if args.high_value or args.high_value_only:
            console.print("\n[bold cyan]Phase 2: High-value file type search[/bold cyan]")
            console.print("[dim]Scanning: .bash_history, AndroidManifest.xml, .ipynb, next.config.js, etc.[/dim]\n")
            path_results = scanner.search_by_path(
                from_iter=args.from_iter if args.high_value_only else 0,
                max_pages=args.max_pages
            )
            results.extend(path_results)
            console.print(f"[green]Found {len(path_results)} keys from high-value files[/green]")
        
        console.print(f"\n[bold]Total: Found {len(results)} potential API keys[/bold]\n")
        
        # Add keys to database
        for api_key, source_url, file_path, language in results:
            if db.add_key(api_key, source_url, file_path, language):
                new_keys += 1
        
        console.print(f"[green]Added {new_keys} new keys to database[/green]")
        
        scanner.close()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Scan interrupted by user.[/yellow]")
    except Exception as e:
        console.print(f"[bold red]Error during scan: {e}[/bold red]")
        if args.debug:
            import traceback
            traceback.print_exc()
    
    # Validate newly found keys
    console.print("\n[bold]Validating discovered keys...[/bold]")
    validate_keys(db, validator)
    
    # Show final summary
    console.print("\n")
    display_summary(db)
    display_valid_keys(db)
    
    db.close()
    console.print("\n[dim]Results saved to database.[/dim]")


if __name__ == "__main__":
    main()
