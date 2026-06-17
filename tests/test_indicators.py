"""Unit tests for the deterministic indicator functions.

These are the numbers the agent reports, so correctness here is the whole
reliability story. No network, no DB — pure math.
"""
import math

import pytest

from app.services import indicators as ind


# ── SMA / EMA ─────────────────────────────────────────────────────────────────

def test_sma_basic():
    assert ind.sma([1, 2, 3, 4, 5], 5) == 3.0
    assert ind.sma([2, 4, 6, 8], 2) == 7.0  # mean of last two (6,8)


def test_sma_insufficient_data():
    assert ind.sma([1, 2], 5) is None


def test_ema_matches_known_value():
    # EMA over a constant series equals the constant.
    assert ind.ema([5.0] * 30, 10) == pytest.approx(5.0)


def test_ema_insufficient_data():
    assert ind.ema([1, 2, 3], 10) is None


# ── RSI ───────────────────────────────────────────────────────────────────────

def test_rsi_all_gains_is_100():
    assert ind.rsi(list(range(1, 40)), 14) == 100.0


def test_rsi_all_losses_is_0():
    assert ind.rsi(list(range(40, 1, -1)), 14) == 0.0


def test_rsi_bounds_and_midrange():
    # An alternating series should land somewhere in the middle, within [0,100].
    series = [10 + (i % 2) for i in range(40)]
    val = ind.rsi(series, 14)
    assert val is not None and 0.0 <= val <= 100.0


def test_rsi_insufficient_data():
    assert ind.rsi([1, 2, 3], 14) is None


# ── MACD ──────────────────────────────────────────────────────────────────────

def test_macd_constant_series_is_zero():
    m = ind.macd([100.0] * 60)
    assert m is not None
    assert m["macd"] == pytest.approx(0.0, abs=1e-6)
    assert m["histogram"] == pytest.approx(0.0, abs=1e-6)


def test_macd_insufficient_data():
    assert ind.macd([1, 2, 3]) is None


def test_macd_uptrend_is_positive():
    m = ind.macd([float(i) for i in range(1, 80)])
    assert m is not None and m["macd"] > 0


# ── Volatility / returns / drawdown ───────────────────────────────────────────

def test_total_return():
    assert ind.total_return([100, 150]) == pytest.approx(0.5)
    assert ind.total_return([100, 50]) == pytest.approx(-0.5)


def test_total_return_insufficient():
    assert ind.total_return([100]) is None


def test_max_drawdown():
    # 100 → 120 → 60 → 90: worst trough 60 against peak 120 = -50%.
    assert ind.max_drawdown([100, 120, 60, 90]) == pytest.approx(-0.5)


def test_max_drawdown_monotonic_up_is_zero():
    assert ind.max_drawdown([1, 2, 3, 4, 5]) == pytest.approx(0.0)


def test_annualized_volatility_constant_is_zero():
    assert ind.annualized_volatility([100.0] * 30) == pytest.approx(0.0)


def test_annualized_volatility_positive():
    series = [100 * (1.01 ** i) * (1 + (-1) ** i * 0.02) for i in range(60)]
    vol = ind.annualized_volatility(series)
    assert vol is not None and vol > 0


# ── Summary panel ─────────────────────────────────────────────────────────────

def test_summary_keys_and_count():
    closes = [float(x) for x in range(1, 120)]
    s = ind.summary(closes)
    expected = {
        "last_close", "sma_20", "sma_50", "ema_20", "rsi_14", "macd",
        "annualized_volatility", "total_return", "max_drawdown", "data_points",
    }
    assert set(s) == expected
    assert s["data_points"] == 119
    assert s["last_close"] == 119.0


def test_summary_handles_short_series_gracefully():
    s = ind.summary([10.0, 11.0])
    assert s["data_points"] == 2
    assert s["sma_50"] is None      # not enough data
    assert s["total_return"] == pytest.approx(0.1)
