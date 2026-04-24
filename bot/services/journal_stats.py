"""Trading stats computation."""
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select

from bot.db import session_scope
from bot.models import Trade


@dataclass
class Stats:
    total: int
    wins: int
    losses: int
    winrate: Decimal
    total_pnl: Decimal
    avg_win: Decimal
    avg_loss: Decimal
    avg_rr: Decimal


async def compute_stats(user_id: int) -> Stats | None:
    async with session_scope() as s:
        res = await s.execute(
            select(Trade).where(Trade.user_id == user_id, Trade.status == "closed")
        )
        trades = list(res.scalars().all())

    if not trades:
        return None

    wins = [t for t in trades if t.pnl is not None and t.pnl > 0]
    losses = [t for t in trades if t.pnl is not None and t.pnl < 0]
    total_pnl = sum((t.pnl or Decimal(0) for t in trades), Decimal(0))
    avg_win = (sum((t.pnl for t in wins), Decimal(0)) / len(wins)) if wins else Decimal(0)
    avg_loss = (sum((t.pnl for t in losses), Decimal(0)) / len(losses)) if losses else Decimal(0)
    winrate = (Decimal(len(wins)) / Decimal(len(trades)) * Decimal(100)) if trades else Decimal(0)

    # Per-trade R:R = |actual gain| / |risk distance entry↔SL|. Fall back to PnL ratio.
    rr_vals: list[Decimal] = []
    for t in trades:
        if t.sl is None or t.entry == t.sl or t.pnl is None:
            continue
        risk = abs(t.entry - t.sl) * t.size
        if risk > 0:
            rr_vals.append(abs(t.pnl) / risk * (Decimal(1) if t.pnl >= 0 else Decimal(-1)))
    avg_rr = (sum(rr_vals, Decimal(0)) / len(rr_vals)) if rr_vals else Decimal(0)

    return Stats(
        total=len(trades),
        wins=len(wins),
        losses=len(losses),
        winrate=winrate.quantize(Decimal("0.01")),
        total_pnl=total_pnl.quantize(Decimal("0.01")),
        avg_win=avg_win.quantize(Decimal("0.01")),
        avg_loss=avg_loss.quantize(Decimal("0.01")),
        avg_rr=avg_rr.quantize(Decimal("0.01")),
    )


def pnl_of(side: str, entry: Decimal, exit_: Decimal, size: Decimal) -> Decimal:
    """Simple linear PnL for both long and short."""
    if side == "long":
        return (exit_ - entry) * size
    return (entry - exit_) * size
