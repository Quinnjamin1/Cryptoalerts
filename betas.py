import json
import time
import urllib.request
from datetime import datetime, timezone

# coin: (Yahoo ticker, Kraken pair or None)
COINS = {
    "BTC": ("BTC-USD", "XBTUSD"),
    "ETH": ("ETH-USD", "ETHUSD"),
    "SOL": ("SOL-USD", "SOLUSD"),
    "ZEC": ("ZEC-USD", "ZECUSD"),
    "BNB": ("BNB-USD", None),
    "XRP": ("XRP-USD", "XRPUSD"),
    "NEAR": ("NEAR-USD", "NEARUSD"),
    "HYPE": ("HYPE32196-USD", "HYPEUSD"),
    "DOGE": ("DOGE-USD", "XDGUSD"),
}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def day(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def yahoo(ticker):
    j = get("https://query1.finance.yahoo.com/v8/finance/chart/" + ticker
            + "?interval=1wk&range=max")
    r = j["chart"]["result"][0]
    closes = r["indicators"]["quote"][0]["close"]
    return {day(t): c for t, c in zip(r["timestamp"], closes) if c}


def kraken(pair):
    j = get("https://api.kraken.com/0/public/OHLC?pair=" + pair + "&interval=10080")
    if j.get("error"):
        raise Exception(j["error"])
    rows = [v for k, v in j["result"].items() if k != "last"][0]
    return {day(r[0]): float(r[4]) for r in rows if float(r[4]) > 0}


def weekly_closes(sym):
    y, k = COINS[sym]
    errors = []
    for name, fn, arg in (("yahoo", yahoo, y), ("kraken", kraken, k)):
        if not arg:
            continue
        try:
            w = fn(arg)
            if len(w) > 10:
                return name, w
            errors.append(f"{name}: too little data")
        except Exception as e:
            errors.append(f"{name}: {e}")
    raise Exception("; ".join(errors))


if __name__ == "__main__":
    for sym in COINS:
        try:
            src, w = weekly_closes(sym)
            d = sorted(w)
            print(f"{sym} [{src}]: {len(d)} weeks, {d[0]} to {d[-1]}, last close {w[d[-1]]:,.4g}")
        except Exception as e:
            print(f"{sym}: FAILED ({e})")
        time.sleep(1)
