from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

import yfinance as yf


@dataclass(frozen=True)
class CuratedAsset:
    name: str
    symbol: str
    exchange: str
    currency: str
    yahoo_symbol: str
    asset_class: str
    country_code: str | None


CURATED_ASSETS: list[CuratedAsset] = [
    CuratedAsset("Petrobras PN", "PETR4", "B3", "BRL", "PETR4.SA", "equity", "BR"),
    CuratedAsset("Vale ON", "VALE3", "B3", "BRL", "VALE3.SA", "equity", "BR"),
    CuratedAsset("Itaú Unibanco PN", "ITUB4", "B3", "BRL", "ITUB4.SA", "equity", "BR"),
    CuratedAsset("WEG ON", "WEGE3", "B3", "BRL", "WEGE3.SA", "equity", "BR"),
    CuratedAsset("Apple Inc.", "AAPL", "NASDAQ", "USD", "AAPL", "equity", "US"),
    CuratedAsset("Microsoft Corp.", "MSFT", "NASDAQ", "USD", "MSFT", "equity", "US"),
    CuratedAsset("NVIDIA Corp.", "NVDA", "NASDAQ", "USD", "NVDA", "equity", "US"),
    CuratedAsset("Amazon.com Inc.", "AMZN", "NASDAQ", "USD", "AMZN", "equity", "US"),
    CuratedAsset("Alphabet Inc. C", "GOOG", "NASDAQ", "USD", "GOOG", "equity", "US"),
    CuratedAsset("Tesla Inc.", "TSLA", "NASDAQ", "USD", "TSLA", "equity", "US"),
    CuratedAsset("Toyota Motor", "7203", "TSE", "JPY", "7203.T", "equity", "JP"),
    CuratedAsset("Sony Group", "6758", "TSE", "JPY", "6758.T", "equity", "JP"),
    CuratedAsset("Mitsubishi UFJ", "8306", "TSE", "JPY", "8306.T", "equity", "JP"),
    CuratedAsset("Keyence", "6861", "TSE", "JPY", "6861.T", "equity", "JP"),
    CuratedAsset("Nintendo", "7974", "TSE", "JPY", "7974.T", "equity", "JP"),
    CuratedAsset("SoftBank Group", "9984", "TSE", "JPY", "9984.T", "equity", "JP"),
    CuratedAsset("Bitcoin", "BTC", "CRYPTO", "USD", "BTC-USD", "crypto", None),
    CuratedAsset("Ethereum", "ETH", "CRYPTO", "USD", "ETH-USD", "crypto", None),
    CuratedAsset("Solana", "SOL", "CRYPTO", "USD", "SOL-USD", "crypto", None),
    CuratedAsset("BNB", "BNB", "CRYPTO", "USD", "BNB-USD", "crypto", None),
]


FALLBACK_PRICES: dict[str, float] = {
    "PETR4": 37.0,
    "VALE3": 63.0,
    "ITUB4": 33.0,
    "WEGE3": 49.0,
    "AAPL": 210.0,
    "MSFT": 425.0,
    "NVDA": 122.0,
    "AMZN": 185.0,
    "GOOG": 173.0,
    "TSLA": 250.0,
    "7203": 2900.0,
    "6758": 13200.0,
    "8306": 1750.0,
    "6861": 64000.0,
    "7974": 8300.0,
    "9984": 8600.0,
    "BTC": 69000.0,
    "ETH": 3600.0,
    "SOL": 170.0,
    "BNB": 590.0,
}

FALLBACK_CURRENCY_RATES_TO_BRL: dict[str, float] = {
    "BRL": 1.0,
    "USD": 5.0,
    "EUR": 5.5,
    "GBP": 6.4,
    "JPY": 0.033,
}


def _latest_close(symbol: str) -> float | None:
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(lambda: yf.Ticker(symbol).history(period="5d", interval="1d", auto_adjust=False))
            history = future.result(timeout=5)
    except (FuturesTimeoutError, Exception):
        return None
    
    if history.empty or "Close" not in history:
        return None
    closes = history["Close"].dropna()
    if closes.empty:
        return None
    return float(closes.iloc[-1])


def get_fx_rates_to_brl() -> dict[str, float]:
    symbols = ["BRL=X", "JPY=X", "EURBRL=X", "GBPBRL=X"]
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = dict(zip(symbols, executor.map(_latest_close, symbols)))
    
    usd_brl = results["BRL=X"]
    usd_jpy = results["JPY=X"]
    eur_brl = results["EURBRL=X"]
    gbp_brl = results["GBPBRL=X"]

    if usd_brl is None:
        usd_brl = FALLBACK_CURRENCY_RATES_TO_BRL["USD"]

    jpy_brl = (usd_brl / usd_jpy) if usd_jpy and usd_jpy != 0 else FALLBACK_CURRENCY_RATES_TO_BRL["JPY"]

    return {
        "BRL": 1.0,
        "USD": float(usd_brl),
        "EUR": float(eur_brl if eur_brl is not None else FALLBACK_CURRENCY_RATES_TO_BRL["EUR"]),
        "GBP": float(gbp_brl if gbp_brl is not None else FALLBACK_CURRENCY_RATES_TO_BRL["GBP"]),
        "JPY": float(jpy_brl),
    }


def build_currency_rates_payload() -> list[dict[str, Any]]:
    rates = get_fx_rates_to_brl()
    now = datetime.now(timezone.utc).isoformat()
    return [
        {
            "base_currency": base_currency,
            "quote_currency": "BRL",
            "rate": rate,
            "source": "yfinance",
            "collected_at": now,
        }
        for base_currency, rate in rates.items()
    ]


def build_live_snapshot_payload() -> dict[str, Any]:
    fx_to_brl = get_fx_rates_to_brl()
    assets_payload: list[dict[str, Any]] = []
    live_count = 0

    # Fetch all asset prices in parallel
    with ThreadPoolExecutor(max_workers=8) as executor:
        yahoo_symbols = [asset.yahoo_symbol for asset in CURATED_ASSETS]
        prices = dict(zip(yahoo_symbols, executor.map(_latest_close, yahoo_symbols)))

    for asset in CURATED_ASSETS:
        live_price = prices.get(asset.yahoo_symbol)
        price = live_price if live_price is not None else FALLBACK_PRICES.get(asset.symbol)
        if live_price is not None:
            live_count += 1

        fx = fx_to_brl.get(asset.currency, 1.0)
        valuation_brl = (price * fx) if price is not None else None

        assets_payload.append(
            {
                "name": asset.name,
                "symbol": asset.symbol,
                "exchange": asset.exchange,
                "currency": asset.currency,
                "asset_class": asset.asset_class,
                "country_code": asset.country_code,
                "price": price,
                "fx_to_brl": fx,
                "valuation_brl": valuation_brl,
                "data_quality": "live" if live_price is not None else "fallback",
                "fundamentals": {
                    "pe_ttm": None,
                    "market_cap": None,
                },
            }
        )

    return {
        "base_currency": "BRL",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "asset_count": len(CURATED_ASSETS),
        "live_asset_count": live_count,
        "fallback_asset_count": len(CURATED_ASSETS) - live_count,
        "fx_to_brl": fx_to_brl,
        "provider": "yfinance",
        "assets": assets_payload,
    }
