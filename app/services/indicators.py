"""Technical indicators — pure functions over a price series.

CRITICAL DESIGN CHOICE: every number the agent reports is computed *here*, in
deterministic Python, not by the LLM. The LLM only narrates pre-computed values.
This eliminates arithmetic hallucination — a key reliability talking point.

All functions take a list of closing prices (oldest → newest) and return floats
or lists. They never touch the network.
"""
from __future__ import annotations

import math


def _sma(values: list[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return sum(values[-window:]) / window


def sma(closes: list[float], window: int = 20) -> float | None:
    """Simple moving average of the most recent `window` closes."""
    return _sma(closes, window)


def ema(closes: list[float], window: int = 20) -> float | None:
    """Exponential moving average (most recent value)."""
    if len(closes) < window:
        return None
    k = 2 / (window + 1)
    ema_val = sum(closes[:window]) / window  # seed with SMA
    for price in closes[window:]:
        ema_val = price * k + ema_val * (1 - k)
    return ema_val


def rsi(closes: list[float], period: int = 14) -> float | None:
    """Relative Strength Index (Wilder's smoothing). 0–100.

    >70 commonly read as overbought, <30 as oversold.
    """
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for prev, cur in zip(closes[:-1], closes[1:]):
        change = cur - prev
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for g, l in zip(gains[period:], losses[period:]):
        avg_gain = (avg_gain * (period - 1) + g) / period
        avg_loss = (avg_loss * (period - 1) + l) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(
    closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> dict | None:
    """MACD line, signal line, and histogram (most recent values)."""
    if len(closes) < slow + signal:
        return None

    def ema_series(values: list[float], window: int) -> list[float]:
        k = 2 / (window + 1)
        out = [sum(values[:window]) / window]
        for price in values[window:]:
            out.append(price * k + out[-1] * (1 - k))
        return out

    fast_e = ema_series(closes, fast)
    slow_e = ema_series(closes, slow)
    # align the two EMA series to the same (shorter) length
    n = min(len(fast_e), len(slow_e))
    macd_line = [f - s for f, s in zip(fast_e[-n:], slow_e[-n:])]
    if len(macd_line) < signal:
        return None
    signal_line = ema_series(macd_line, signal)
    return {
        "macd": round(macd_line[-1], 4),
        "signal": round(signal_line[-1], 4),
        "histogram": round(macd_line[-1] - signal_line[-1], 4),
    }


def annualized_volatility(closes: list[float], trading_days: int = 252) -> float | None:
    """Annualized volatility from daily log returns, as a fraction (0.32 = 32%)."""
    if len(closes) < 2:
        return None
    rets = [math.log(b / a) for a, b in zip(closes[:-1], closes[1:]) if a > 0]
    if len(rets) < 2:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return math.sqrt(var) * math.sqrt(trading_days)


def total_return(closes: list[float]) -> float | None:
    """Total return over the series, as a fraction (0.15 = +15%)."""
    if len(closes) < 2 or closes[0] == 0:
        return None
    return closes[-1] / closes[0] - 1


def max_drawdown(closes: list[float]) -> float | None:
    """Largest peak-to-trough decline over the series, as a negative fraction."""
    if len(closes) < 2:
        return None
    peak = closes[0]
    mdd = 0.0
    for price in closes:
        peak = max(peak, price)
        if peak > 0:
            mdd = min(mdd, price / peak - 1)
    return mdd


def summary(closes: list[float]) -> dict:
    """Compute the full indicator panel in one call. Missing values → None."""
    return {
        "last_close": closes[-1] if closes else None,
        "sma_20": sma(closes, 20),
        "sma_50": sma(closes, 50),
        "ema_20": ema(closes, 20),
        "rsi_14": rsi(closes, 14),
        "macd": macd(closes),
        "annualized_volatility": annualized_volatility(closes),
        "total_return": total_return(closes),
        "max_drawdown": max_drawdown(closes),
        "data_points": len(closes),
    }
