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

# Your buy targets from your notes, for when BTC is at ANCHOR_BTC. Edit, then commit.
ANCHOR_BTC = 78000
ANCHORS = {"ETH": 2400, "SOL": 101, "XRP": 1.36, "BNB": 730,
           "DOGE": 0.085, "HYPE": 60, "ZEC": 1350, "NEAR": 3.88}

DIP = float(os.environ.get("DIP", "3"))      # a "dip week" = BTC down at least this %
MIN_N = int(os.environ.get("MIN_N", "15"))   # cycles with fewer dip weeks are skipped
FLOOR = 0.5                                  # betas below this are raised to it

# 4-year cycles, split at the halvings (week-ending Sunday dates)
CYCLES = [
    ("C1 2017-20", "2017-01-01", "2020-05-10"),
    ("C2 2020-24", "2020-05-11", "2024-04-19"),
    ("C3 2024-now", "2024-04-20", "2099-01-01"),
]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def history(ticker):
    """Daily history -> (Sunday close of every completed week, latest price)."""
    j = get("https://query1.finance.yahoo.com/v8/finance/chart/" + ticker
            + "?interval=1d&period1=1483228800&period2=" + str(int(time.time()) + 86400))
    r = j["chart"]["result"][0]
    closes = r["indicators"]["quote"][0]["close"]
    today = datetime.now(timezone.utc).date()
    weekly, last = {}, None
    for t, c in zip(r["timestamp"], closes):
        if not c:
            continue
        last = c
        d = datetime.fromtimestamp(t, tz=timezone.utc).date()
        if d.weekday() == 6 and d < today:
            weekly[d.isoformat()] = c
    return weekly, last


def weekly_returns(closes):
    out = {}
    for d, c in closes.items():
        prev = (date.fromisoformat(d) - timedelta(days=7)).isoformat()
        if prev in closes:
            out[d] = c / closes[prev] - 1
    return out


def main():
    rets, price = {}, {}
    for sym, tick in TICKERS.items():
        try:
            weekly, price[sym] = history(tick)
            rets[sym] = weekly_returns(weekly)
        except Exception as e:
            print(f"{sym}: FAILED ({e})")
        time.sleep(1)

    btc = rets["BTC"]
    dips = {d: r for d, r in btc.items() if r <= -DIP / 100}

    # beta per cycle = typical (median) alt move / typical (median) BTC move in dip weeks
    betas, detail = {}, {}
    for sym in rets:
        if sym == "BTC":
            continue
        per = []
        for name, a, b in CYCLES:
            ds = [d for d in dips if a <= d <= b and d in rets[sym]]
            if len(ds) >= MIN_N:
                beta = (statistics.median(rets[sym][d] for d in ds)
                        / statistics.median(dips[d] for d in ds))
                per.append((name.split()[0], beta, len(ds)))
        if per:
            betas[sym] = statistics.mean(b for _, b, _ in per)
            detail[sym] = per

    print("Beta = typical alt move / typical BTC move in BTC dip weeks")
    for sym, per in detail.items():
        cyc = " | ".join(f"{c} {b:.1f}x n{n}" for c, b, n in per)
        print(f"{sym} {betas[sym]:.1f}x ({cyc})")

    ratio = price["BTC"] / ANCHOR_BTC
    print(f"\nBTC now {price['BTC']:,.0f}, your anchor {ANCHOR_BTC:,}")
    print("slid target = your 78k target x (BTC now / 78k) ^ beta\n")
    slid = {}
    for sym, anchor in ANCHORS.items():
        if sym not in betas or sym not in price:
            print(f"{sym}: no data")
            continue
        used = max(betas[sym], FLOOR)
        slid[sym] = anchor * ratio ** used
        p = price[sym]
        n1 = "under" if p <= anchor else "over"
        n2 = "under" if p <= slid[sym] else "over"
        flo = " floored" if used != betas[sym] else ""
        print(f"{sym} now {p:,.4g} | note {anchor:,.4g} {n1} | slid {slid[sym]:,.4g} {n2}{flo}")

    out = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "btc_price": price["BTC"],
        "anchor_btc": ANCHOR_BTC,
        "betas": {k: round(v, 3) for k, v in betas.items()},
        "slid_targets": {k: round(v, 6) for k, v in slid.items()},
    }
    with open("betas.json", "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()


