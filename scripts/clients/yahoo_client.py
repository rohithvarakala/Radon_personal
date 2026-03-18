"""Yahoo Finance client — free alternative to Unusual Whales.

Uses the yfinance library for stock info, options chains, analyst data,
and historical prices. No API key required.
"""

import yfinance as yf
from datetime import datetime, timedelta
from typing import Any


class YahooClient:
    """Client for Yahoo Finance data via yfinance."""

    def __init__(self):
        pass

    def _get_ticker(self, symbol: str) -> yf.Ticker:
        """Get yfinance Ticker object."""
        return yf.Ticker(symbol.upper())

    # --- Stock Info ---

    def get_stock_info(self, symbol: str) -> dict:
        """Get stock information for ticker validation."""
        t = self._get_ticker(symbol)
        info = t.info
        return {
            "ticker": symbol.upper(),
            "name": info.get("longName") or info.get("shortName", ""),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "market_cap": info.get("marketCap"),
            "price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "previous_close": info.get("previousClose"),
            "volume": info.get("volume"),
            "avg_volume": info.get("averageVolume"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "dividend_yield": info.get("dividendYield"),
            "beta": info.get("beta"),
            "short_ratio": info.get("shortRatio"),
            "short_percent_of_float": info.get("shortPercentOfFloat"),
        }

    def validate_ticker(self, symbol: str) -> bool:
        """Check if a ticker symbol is valid."""
        try:
            t = self._get_ticker(symbol)
            info = t.info
            return bool(info.get("regularMarketPrice") or info.get("currentPrice"))
        except Exception:
            return False

    # --- Options Chain ---

    def get_option_chain(self, symbol: str, expiry: str | None = None) -> dict:
        """Get options chain for a ticker.

        Args:
            symbol: Ticker symbol.
            expiry: Optional expiration date string (YYYY-MM-DD).
                    If None, returns nearest expiry.

        Returns:
            Dict with calls, puts, and expiration dates.
        """
        t = self._get_ticker(symbol)
        expirations = t.options

        if not expirations:
            return {"ticker": symbol, "expirations": [], "calls": [], "puts": []}

        target_expiry = expiry if expiry and expiry in expirations else expirations[0]
        chain = t.option_chain(target_expiry)

        return {
            "ticker": symbol.upper(),
            "expiry": target_expiry,
            "expirations": list(expirations),
            "calls": chain.calls.to_dict("records") if not chain.calls.empty else [],
            "puts": chain.puts.to_dict("records") if not chain.puts.empty else [],
        }

    def get_all_expirations(self, symbol: str) -> list[str]:
        """Get all available option expiration dates."""
        t = self._get_ticker(symbol)
        return list(t.options)

    # --- Analyst Data ---

    def get_analyst_ratings(self, symbol: str) -> dict:
        """Get analyst recommendations and price targets."""
        t = self._get_ticker(symbol)
        info = t.info

        recommendations = []
        try:
            recs = t.recommendations
            if recs is not None and not recs.empty:
                recommendations = recs.tail(20).to_dict("records")
        except Exception:
            pass

        return {
            "ticker": symbol.upper(),
            "target_mean_price": info.get("targetMeanPrice"),
            "target_high_price": info.get("targetHighPrice"),
            "target_low_price": info.get("targetLowPrice"),
            "recommendation_key": info.get("recommendationKey"),
            "number_of_analyst_opinions": info.get("numberOfAnalystOpinions"),
            "recommendations": recommendations,
        }

    # --- Historical Prices ---

    def get_price_history(
        self,
        symbol: str,
        period: str = "3mo",
        interval: str = "1d",
    ) -> list[dict]:
        """Get historical price data.

        Args:
            symbol: Ticker symbol.
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max).
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo).

        Returns:
            List of OHLCV dicts.
        """
        t = self._get_ticker(symbol)
        hist = t.history(period=period, interval=interval)

        if hist.empty:
            return []

        records = []
        for date, row in hist.iterrows():
            records.append({
                "date": str(date.date()) if hasattr(date, "date") else str(date),
                "open": round(row["Open"], 2),
                "high": round(row["High"], 2),
                "low": round(row["Low"], 2),
                "close": round(row["Close"], 2),
                "volume": int(row["Volume"]),
            })
        return records

    # --- Implied Volatility ---

    def get_iv_data(self, symbol: str) -> dict:
        """Get implied volatility data from options chain.

        Extracts IV from the nearest ATM options to estimate overall IV.
        """
        t = self._get_ticker(symbol)
        info = t.info
        current_price = info.get("currentPrice") or info.get("regularMarketPrice")

        if not current_price or not t.options:
            return {"ticker": symbol, "iv": None}

        nearest_expiry = t.options[0]
        chain = t.option_chain(nearest_expiry)

        # Find ATM options (closest strike to current price)
        if not chain.calls.empty:
            calls = chain.calls
            atm_idx = (calls["strike"] - current_price).abs().idxmin()
            atm_call_iv = calls.loc[atm_idx, "impliedVolatility"]
        else:
            atm_call_iv = None

        if not chain.puts.empty:
            puts = chain.puts
            atm_idx = (puts["strike"] - current_price).abs().idxmin()
            atm_put_iv = puts.loc[atm_idx, "impliedVolatility"]
        else:
            atm_put_iv = None

        # Average ATM call/put IV
        ivs = [v for v in [atm_call_iv, atm_put_iv] if v is not None]
        avg_iv = sum(ivs) / len(ivs) if ivs else None

        return {
            "ticker": symbol.upper(),
            "current_price": current_price,
            "nearest_expiry": nearest_expiry,
            "atm_call_iv": round(atm_call_iv, 4) if atm_call_iv else None,
            "atm_put_iv": round(atm_put_iv, 4) if atm_put_iv else None,
            "avg_atm_iv": round(avg_iv, 4) if avg_iv else None,
        }

    # --- Short Interest ---

    def get_short_interest(self, symbol: str) -> dict:
        """Get short interest data."""
        info = self._get_ticker(symbol).info
        return {
            "ticker": symbol.upper(),
            "short_ratio": info.get("shortRatio"),
            "short_percent_of_float": info.get("shortPercentOfFloat"),
            "shares_short": info.get("sharesShort"),
            "shares_short_prior_month": info.get("sharesShortPriorMonth"),
            "date_short_interest": info.get("dateShortInterest"),
        }

    # --- Institutional Holders ---

    def get_institutional_holders(self, symbol: str) -> list[dict]:
        """Get institutional holders as proxy for institutional flow."""
        t = self._get_ticker(symbol)
        try:
            holders = t.institutional_holders
            if holders is not None and not holders.empty:
                return holders.to_dict("records")
        except Exception:
            pass
        return []

    # --- Put/Call Ratio (derived) ---

    def get_put_call_ratio(self, symbol: str) -> dict:
        """Calculate put/call ratio from options chain volume.

        Signal interpretation:
        >2.0 BEARISH | 1.2-2.0 LEAN_BEARISH | 0.8-1.2 NEUTRAL
        0.5-0.8 LEAN_BULLISH | <0.5 BULLISH
        """
        t = self._get_ticker(symbol)
        if not t.options:
            return {"ticker": symbol, "ratio": None, "signal": "NO_DATA"}

        total_call_vol = 0
        total_put_vol = 0

        # Aggregate across first 3 expirations for meaningful ratio
        for expiry in t.options[:3]:
            chain = t.option_chain(expiry)
            if not chain.calls.empty:
                total_call_vol += chain.calls["volume"].sum()
            if not chain.puts.empty:
                total_put_vol += chain.puts["volume"].sum()

        if total_call_vol == 0:
            return {"ticker": symbol, "ratio": None, "signal": "NO_DATA"}

        ratio = total_put_vol / total_call_vol

        if ratio > 2.0:
            signal = "BEARISH"
        elif ratio > 1.2:
            signal = "LEAN_BEARISH"
        elif ratio > 0.8:
            signal = "NEUTRAL"
        elif ratio > 0.5:
            signal = "LEAN_BULLISH"
        else:
            signal = "BULLISH"

        return {
            "ticker": symbol.upper(),
            "ratio": round(ratio, 3),
            "signal": signal,
            "total_call_volume": int(total_call_vol),
            "total_put_volume": int(total_put_vol),
        }
