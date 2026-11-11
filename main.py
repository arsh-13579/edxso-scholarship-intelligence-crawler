import argparse
import sqlite3
from rich.console import Console
from rich.table import Table
from src.config import Config
from src.database import init_db, upsert_scholarship_with_change_detection, log_crawl_run, export_csv_reports
from src.discovery import ScholarshipDiscoveryEngine
from src.crawler import ScholarshipCrawler
from src.extractor import AntiHallucinationExtractor
from src.verifier import DeterministicVerificationEngine

console = Console()

def execute_crawler_run(run_number: int):
    console.rule(f"[bold cyan]Atlas Scholarship Intelligence Crawler — Automated Run #{run_number}")
    init_db()

    conn = sqlite3.connect(Config.DB_PATH)
    before_count = conn.execute("SELECT COUNT(*) FROM scholarships").fetchone()[0]
    conn.close()

    discovery = ScholarshipDiscoveryEngine()
    crawler = ScholarshipCrawler()
    extractor = AntiHallucinationExtractor()
    verifier = DeterministicVerificationEngine()

    console.print(f"\n[bold yellow]1. Discovering Scholarships from Seed Portals & Link Graph (Run #{run_number})...[/bold yellow]")
    discovered_nodes = discovery.discover_opportunities(run_number=run_number)
    console.print(f"[green]✔ Discovered {len(discovered_nodes)} candidate scholarship opportunities across 5 source categories.[/green]")

    console.print("\n[bold yellow]2. Crawling Primary Sources, Extracting 20-Field Schema & Running 8-Point Verification Engine...[/bold yellow]")
    all_changes = []
    verified_count = 0

    table = Table(title=f"Scholarship Intelligence Summary (Run #{run_number})", show_lines=False)
    table.add_column("ID", style="dim")
    table.add_column("Scholarship Name", style="cyan", max_width=38)
    table.add_column("Source Type", style="magenta")
    table.add_column("Deadline", style="yellow")
    table.add_column("Confidence", justify="right", style="bold green")
    table.add_column("Verification", style="bold")
    table.add_column("Lifecycle Status", style="bold")

    for node in discovered_nodes:
        crawled = crawler.crawl_source(node)
        extracted = extractor.extract_structured_record(crawled)
        verified_record = verifier.verify_and_score(extracted, crawled)

        if verified_record["verification_label"] == "VERIFIED":
            verified_count += 1

        changes = upsert_scholarship_with_change_detection(verified_record, run_number=run_number)
        all_changes.extend(changes)

        table.add_row(
            verified_record["scholarship_id"],
            verified_record["name"],
            verified_record["source_type"],
            verified_record["closing_date"].split("(")[0].strip(),
            f"{verified_record['confidence_score']}%",
            verified_record["verification_label"],
            verified_record["status"]
        )

    console.print(table)

    conn = sqlite3.connect(Config.DB_PATH)
    after_count = conn.execute("SELECT COUNT(*) FROM scholarships").fetchone()[0]
    conn.close()
    new_added = max(0, after_count - before_count)

    log_crawl_run(
        run_number=run_number,
        discovered=len(discovered_nodes),
        verified=verified_count,
        changes=len(all_changes),
        new_added=new_added
    )

    if all_changes:
        console.print(f"\n[bold red]⚡ CHANGE DETECTION ENGINE: {len(all_changes)} Official Updates Detected in Run #{run_number}![/bold red]")
        for c in all_changes:
            console.print(
                f"  • [bold]{c['scholarship_name']}[/bold] | Field `{c['field']}`: "
                f"[red]{c['old']}[/red] ➔ [green]{c['new']}[/green]"
            )
    else:
        console.print(f"\n[bold green]✔ Run #{run_number} Baseline Stored: {after_count} scholarships indexed ({verified_count} VERIFIED >=95%).[/bold green]")

    export_csv_reports()
    console.print("[bold green]✔ Exported `data/scholarships_repository.csv` and `data/change_detection_log.csv`.[/bold green]\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Atlas Scholarship Intelligence Crawler")
    parser.add_argument("--run", type=int, default=0, help="Run number (1 for initial crawl, 2 for change-detection crawl, 0 to run both sequentially)")
    args = parser.parse_args()

    if args.run == 0:
        execute_crawler_run(1)
        execute_crawler_run(2)
    else:
        execute_crawler_run(args.run)
