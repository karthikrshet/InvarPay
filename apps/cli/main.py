#!/usr/bin/env python3
"""
InvarPay AI — CLI (Phase 2)

Usage:
  payguard status <payment-id>
  payguard reconcile <payment-id>
  payguard investigate <payment-id>
  payguard recovery <payment-id>
  payguard seed
  payguard health
"""
from __future__ import annotations

import json
import os
import sys
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="invarpay",
    help="InvarPay AI — financial operations CLI. Independent open-source tool.",
    no_args_is_help=True,
)
console = Console()

API_URL = os.environ.get("INVARPAY_API_URL") or os.environ.get("PAYGUARD_API_URL", "http://localhost:8000")
API_KEY = os.environ.get("INVARPAY_API_KEY") or os.environ.get("PAYGUARD_API_KEY", "")


def _api(path: str, method: str = "GET", body: Optional[dict] = None) -> dict:
    """Make an API request with the configured key."""
    import urllib.error
    import urllib.request

    url = f"{API_URL}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err = json.loads(e.read())
        console.print(f"[red]API Error {e.code}:[/red] {err.get('detail', str(err))}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Connection error:[/red] {e}")
        console.print(f"Is the API running at {API_URL}? Try: make dev")
        raise typer.Exit(1)


STATUS_COLORS = {
    "captured": "green",
    "authorized": "blue",
    "pending": "yellow",
    "initiated": "cyan",
    "unknown": "bold yellow",
    "failed": "red",
    "cancelled": "dim",
    "created": "dim white",
}


def _color_status(status: str) -> str:
    color = STATUS_COLORS.get(status, "white")
    return f"[{color}]{status}[/{color}]"


@app.command()
def health():
    """Check API health and connectivity."""
    result = _api("/health/ready")
    status = result.get("status", "unknown")
    checks = result.get("checks", {})

    color = "green" if status == "ok" else "yellow"
    console.print(Panel(
        f"Status: [{color}]{status}[/{color}]\n"
        f"Version: {result.get('version', '?')}\n"
        f"Environment: {result.get('environment', '?')}\n"
        f"Database: {'✓' if checks.get('database') else '✗'}\n"
        f"Redis: {'✓' if checks.get('redis') else '✗'}",
        title="InvarPay AI — Health",
        box=box.ROUNDED,
    ))


@app.command()
def status(
    payment_id: str = typer.Argument(..., help="Payment attempt ID"),
):
    """Get payment status and event timeline."""
    if not API_KEY:
        console.print("[red]Set INVARPAY_API_KEY or PAYGUARD_API_KEY environment variable[/red]")
        raise typer.Exit(1)

    result = _api(f"/v1/payments/{payment_id}")

    status_val = result.get("status", "unknown")
    color = STATUS_COLORS.get(status_val, "white")

    console.print(Panel(
        f"ID: [dim]{payment_id}[/dim]\n"
        f"Status: [{color}]{status_val}[/{color}]\n"
        f"Amount: {result.get('currency', 'INR')} {result.get('amount', 0) / 100:.2f}\n"
        f"Provider ID: [dim]{result.get('provider_payment_id') or '—'}[/dim]\n"
        f"Reconciled: {'✓' if result.get('is_reconciled') else '✗'}\n"
        f"Provider events: {len(result.get('provider_events', []))}",
        title="Payment Status",
        box=box.ROUNDED,
    ))

    if status_val == "unknown":
        console.print(
            "\n[bold yellow]⚠  UNKNOWN OUTCOME[/bold yellow]\n"
            "  This payment may already be captured.\n"
            "  DO NOT retry — run: [bold]invarpay reconcile[/bold] first.\n"
        )

    # Timeline
    events = result.get("provider_events", [])
    if events:
        table = Table(title="Provider Events", box=box.SIMPLE)
        table.add_column("Event", style="cyan")
        table.add_column("Verified", justify="center")
        table.add_column("Received")
        for e in events[:10]:
            table.add_row(
                e.get("event_type", "?"),
                "✓" if e.get("signature_verified") else "[red]✗[/red]",
                e.get("received_at", "?")[:19],
            )
        console.print(table)


@app.command()
def reconcile(
    payment_id: str = typer.Argument(..., help="Payment attempt ID"),
):
    """Trigger reconciliation for a payment."""
    console.print(f"[cyan]Reconciling payment {payment_id}...[/cyan]")
    result = _api(f"/v1/payments/{payment_id}/reconcile", method="POST", body={})

    run_status = result.get("status", "?")
    color = "green" if run_status == "completed" else "yellow"
    console.print(
        f"[{color}]Reconciliation {run_status}[/{color}]\n"
        f"  Matched: {result.get('matched_items', 0)}\n"
        f"  Mismatched: {result.get('mismatched_items', 0)}\n"
        f"  Unresolved: {result.get('unresolved_items', 0)}"
    )


@app.command()
def investigate(
    payment_id: str = typer.Argument(..., help="Payment attempt ID"),
    reason: str = typer.Option("", "--reason", "-r", help="Investigation trigger reason"),
):
    """Start an AI investigation for a payment."""
    console.print(f"[cyan]Starting investigation for {payment_id}...[/cyan]")
    result = _api(
        f"/v1/payments/{payment_id}/investigations",
        method="POST",
        body={"trigger_reason": reason or "Requested from CLI"},
    )
    console.print(
        f"Investigation [bold]{result.get('id')}[/bold] started.\n"
        f"Status: {_color_status(result.get('status', 'pending'))}\n"
        f"Check: invarpay investigation-status {result.get('id')}"
    )


@app.command()
def recovery(
    payment_id: str = typer.Argument(..., help="Payment attempt ID"),
):
    """Get deterministic recovery recommendation for a payment."""
    payment = _api(f"/v1/payments/{payment_id}")
    status_val = payment.get("status", "unknown")

    from modules.payguard.recovery import recommend_recovery
    rec = recommend_recovery(
        payment_status=status_val,
        provider_status=payment.get("provider_status"),
        is_reconciled=payment.get("is_reconciled", False),
        provider_payment_id=payment.get("provider_payment_id"),
        initiated_at=None,
        minutes_since_initiation=None,
        failure_code=None,
    )

    risk_colors = {"LOW": "green", "MEDIUM": "yellow", "HIGH": "red", "CRITICAL": "bold red"}
    risk_color = risk_colors.get(rec.estimated_risk, "white")

    console.print(Panel(
        f"Action: [bold]{rec.action.value}[/bold]\n"
        f"Safety: [bold]{rec.safety.value}[/bold]\n"
        f"Risk: [{risk_color}]{rec.estimated_risk}[/{risk_color}]\n"
        f"Requires Approval: {'Yes' if rec.requires_approval else 'No'}\n\n"
        f"{rec.reason}",
        title=f"Recovery Recommendation — {payment_id}",
        box=box.ROUNDED,
    ))


@app.command()
def seed():
    """Seed synthetic demo data into the database."""
    console.print("[cyan]Seeding SYNTHETIC demo data...[/cyan]")
    console.print("[yellow]All data is fictional — not real payments[/yellow]")
    import asyncio
    sys.path.insert(0, ".")
    from examples.demo_merchant.seed import seed_demo_data
    asyncio.run(seed_demo_data())


@app.command()
def orders(
    page: int = typer.Option(1, "--page", "-p"),
    status_filter: Optional[str] = typer.Option(None, "--status", "-s"),
):
    """List orders for the authenticated organization."""
    path = f"/v1/orders?page={page}&page_size=20"
    if status_filter:
        path += f"&status={status_filter}"
    result = _api(path)

    table = Table(title="Orders", box=box.SIMPLE_HEAD)
    table.add_column("ID", style="dim", max_width=28)
    table.add_column("Status")
    table.add_column("Amount", justify="right")
    table.add_column("Fulfilled", justify="center")
    table.add_column("Created")

    for order in result.get("items", []):
        table.add_row(
            order["id"][:20] + "...",
            _color_status(order.get("status", "?")),
            f"{order.get('currency', 'INR')} {order.get('amount', 0) / 100:.2f}",
            "✓" if order.get("is_fulfilled") else "—",
            order.get("created_at", "?")[:10],
        )

    console.print(table)
    total = result.get("total", 0)
    console.print(f"[dim]Total: {total} orders[/dim]")


if __name__ == "__main__":
    app()
