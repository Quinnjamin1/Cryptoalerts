import json
import time
import urllib.request
from datetime import datetime, timezone

COINS = ["BTC", "ETH", "SOL", "ZEC", "BNB", "XRP", "NEAR", "HYPE", "DOGE"]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "price-alerts"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def weekly_closes(sym):
    """Daily history -> weekly closes (the Sunday daily close, UTC)."""
    url = ("https://min-api.cryptocompare.com/data/v2/histoday?fsym=" + sym
           + "&tsym=USD&allData=true")
    rows = get(url)["Data"]["Data"]
    out = {}
    for d in rows:
        if d["close"] <= 0:
            continue
        day = datetime.fromtimestamp(d["time"], tz=timezone.utc)
        if day.weekday() == 6:  # Sunday
            out[day.strftime("%Y-%m-%d")] = d["close"]
    return out


if __name__ == "__main__":
    for sym in COINS:
        try:
            w = weekly_closes(sym)
            dates = sorted(w)
            print(f"{sym}: {len(dates)} weeks, {dates[0]} to {dates[-1]}, last close {w[dates[-1]]:,.4g}")
        except Exception as e:
            print(f"{sym}: FAILED ({e})")
        time.sleep(1.5)
