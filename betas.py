import json
import os
import statistics
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone

TICKERS = {
    "BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD", "ZEC": "ZEC-USD",
    "BNB": "BNB-USD", "XRP": "XRP-USD", "NEAR": "NEAR-USD",
    "HYPE": "HYPE32196-USD", "DOGE": "DOGE-USD",
}
DIP = float(os.environ.get("DIP", "3"))  # a "dip week" = BTC down at least this %

# 4-year cycles, split at the halvings (inclusive dates of the week-ending Sunday)
CYCLES = [
    ("C1 2017-20", "2017-01-01", "2020-05-10"),
    ("C2 2020-24", "2020-05-11", "2024-04-19"),
    ("C3 2024-now", "2024-04-20", "2099-01-01"),
]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def sunday_closes(ticker):
    """Daily history -> the Sunday close (UTC) of every completed week."""
    j = get("https://query1.finance.yahoo.com/v8/finance/chart/" + ticker
            + "?interval=1d&period1=1483228800&period2=" + str(int(time.time()) + 86400))
    r = j["chart"]["result"][0]
    closes = r["indicators"]["quote"][0]["close"]
    today = datetime.now(timezone.utc).date()
    out = {}
    for t, c in zip(r["timestamp"], closes):
        if not c:
            continue
        d = datetime.fromtimestamp(t, tz=timezone.utc).date()
        if d.weekday() == 6 and d < today:
            out[d.isoformat()] = c
    return out


def weekly_returns(closes):
    out = {}
    for d, c in closes.items():
        prev = (date.fromisoformat(d) - timedelta(days=7)).isoformat()
        if prev in closes:
            out[d] = c / closes[prev] - 1
    return out


if __name__ == "__main__":
    rets = {}
    for sym, tick in TICKERS.items():
        try:
            rets[sym] = weekly_returns(sunday_closes(tick))
            d = sorted(rets[sym])
            print(f"{sym}: {len(d)} weekly returns, {d[0]} to {d[-1]}")
        except Exception as e:
            print(f"{sym}: FAILED ({e})")
        time.sleep(1)

    btc = rets["BTC"]
    dips = {d: r for d, r in btc.items() if r <= -DIP / 100}

    print(f"\nBTC weeks down {DIP:g}% or more, by cycle:")
    for name, a, b in CYCLES:
        ds = [d for d in dips if a <= d <= b]
        total = [d for d in btc if a <= d <= b]
        if ds:
            avg = statistics.mean(dips[d] for d in ds)
            worst = min(dips[d] for d in ds)
            print(f"{name}: {len(ds)} dip weeks of {len(total)}, avg {avg:.1%}, worst {worst:.1%}")
        else:
            print(f"{name}: none")

    print("\nDip weeks each coin has data for:")
    for sym in rets:
        if sym == "BTC":
            continue
        parts = []
        for name, a, b in CYCLES:
            n = sum(1 for d in dips if a <= d <= b and d in rets[sym])
            parts.append(f"{name.split()[0]}: {n}")
        print(sym, " | ".join(parts))
