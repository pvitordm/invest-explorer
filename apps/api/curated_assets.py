"""
Curated list of ~20 assets for MVP across BR/US/JP/Crypto.
Format: name, symbol, exchange, currency, asset_class, country_code
"""

CURATED_ASSETS = [
    # Brazil - Top 5
    {"name": "Petrobras PN", "symbol": "PETR4", "exchange": "B3", "currency": "BRL", "asset_class": "equity", "country_code": "BR"},
    {"name": "Vale ON", "symbol": "VALE3", "exchange": "B3", "currency": "BRL", "asset_class": "equity", "country_code": "BR"},
    {"name": "Itaú Unibanco", "symbol": "ITUB4", "exchange": "B3", "currency": "BRL", "asset_class": "equity", "country_code": "BR"},
    {"name": "Bradesco", "symbol": "BBDC4", "exchange": "B3", "currency": "BRL", "asset_class": "equity", "country_code": "BR"},
    {"name": "Natura &Co", "symbol": "NTCO3", "exchange": "B3", "currency": "BRL", "asset_class": "equity", "country_code": "BR"},
    
    # USA - Top 5
    {"name": "Apple Inc.", "symbol": "AAPL", "exchange": "NASDAQ", "currency": "USD", "asset_class": "equity", "country_code": "US"},
    {"name": "Microsoft Corp.", "symbol": "MSFT", "exchange": "NASDAQ", "currency": "USD", "asset_class": "equity", "country_code": "US"},
    {"name": "Amazon.com Inc.", "symbol": "AMZN", "exchange": "NASDAQ", "currency": "USD", "asset_class": "equity", "country_code": "US"},
    {"name": "Alphabet Inc.", "symbol": "GOOGL", "exchange": "NASDAQ", "currency": "USD", "asset_class": "equity", "country_code": "US"},
    {"name": "Tesla Inc.", "symbol": "TSLA", "exchange": "NASDAQ", "currency": "USD", "asset_class": "equity", "country_code": "US"},
    
    # Japan - Top 3
    {"name": "Toyota Motor", "symbol": "7203", "exchange": "TSE", "currency": "JPY", "asset_class": "equity", "country_code": "JP"},
    {"name": "Sony Group", "symbol": "6758", "exchange": "TSE", "currency": "JPY", "asset_class": "equity", "country_code": "JP"},
    {"name": "Honda Motor", "symbol": "7267", "exchange": "TSE", "currency": "JPY", "asset_class": "equity", "country_code": "JP"},
    
    # Crypto - Top 4
    {"name": "Bitcoin", "symbol": "BTC", "exchange": "CRYPTO", "currency": "USD", "asset_class": "crypto", "country_code": "GLOBAL"},
    {"name": "Ethereum", "symbol": "ETH", "exchange": "CRYPTO", "currency": "USD", "asset_class": "crypto", "country_code": "GLOBAL"},
    {"name": "Solana", "symbol": "SOL", "exchange": "CRYPTO", "currency": "USD", "asset_class": "crypto", "country_code": "GLOBAL"},
    {"name": "Cardano", "symbol": "ADA", "exchange": "CRYPTO", "currency": "USD", "asset_class": "crypto", "country_code": "GLOBAL"},
]

# Fallback prices (USD or original currency) for development/offline
FALLBACK_PRICES = {
    # BR - in BRL
    "PETR4": {"price": 37, "currency": "BRL"},
    "VALE3": {"price": 63, "currency": "BRL"},
    "ITUB4": {"price": 28.5, "currency": "BRL"},
    "BBDC4": {"price": 18.2, "currency": "BRL"},
    "NTCO3": {"price": 24.1, "currency": "BRL"},
    # US - USD (will convert to BRL)
    "AAPL": {"price": 210, "currency": "USD"},
    "MSFT": {"price": 425, "currency": "USD"},
    "AMZN": {"price": 195, "currency": "USD"},
    "GOOGL": {"price": 175, "currency": "USD"},
    "TSLA": {"price": 242, "currency": "USD"},
    # JP - JPY (will convert to BRL)
    "7203": {"price": 2900, "currency": "JPY"},
    "6758": {"price": 13200, "currency": "JPY"},
    "7267": {"price": 3400, "currency": "JPY"},
    # Crypto - USD (will convert to BRL)
    "BTC": {"price": 69000, "currency": "USD"},
    "ETH": {"price": 3600, "currency": "USD"},
    "SOL": {"price": 189, "currency": "USD"},
    "ADA": {"price": 1.12, "currency": "USD"},
}

# Approximate FX rates (for fallback/initial dev; use real rates in production)
FX_RATES = {
    "USD": 5.0,  # 1 USD = 5 BRL
    "JPY": 0.033,  # 1 JPY = 0.033 BRL
    "BRL": 1.0,
}
