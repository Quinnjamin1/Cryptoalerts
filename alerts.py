import json
import os
import urllib.request

TOPIC = os.environ["NTFY_TOPIC"]
TARGETS = json.loads(os.environ["TARGETS"])  # your 78k note numbers, by CoinGecko id
STATE = "state.json"
FLOOR = 0.5  # betas below this are raised to it

SYMBOLS = {
    "ethereum": "ETH", "solana": "SOL", "zcash": "ZEC", "binancecoin": "BNB",
    "ripple": "XRP", "near": "NEAR", "hyperliquid": "HYPE", "dogecoin": "DOGE",
}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "price-alerts"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def notify(title, msg):
    req = urllib.request.Request(
        "https://ntfy.sh/" + TOPIC,
        data=msg.encode(),
        headers={"Title": title, "Priority": "high", "Tags": "chart_with_downwards_trend"},
    )
    urllib.request.urlopen(req, timeout=20)


ids = ",".join(sorted(set(TARGETS) | {"bitcoin"}))
prices = get("https://api.coingecko.com/api/v3/simple/price?ids=" + ids + "&vs_currencies=usd")

try:
    with open(STATE) as f:
        fired = set(json.load(f))
except Exception:
    fired = set()

now = set()

# 1) Fixed price targets (same as before; state tag = plain coin id)
for coin, target in TARGETS.items():
    p = prices.get(coin, {}).get("usd")
    if p is None:
        print("no price for", coin)
        if coin in fired:
            now.add(coin)
        continue
    print(coin, p, "target", target)
    if p <= target:
        now.add(coin)
        if coin not in fired:
            notify(f"{coin} hit your target",
                   f"{coin} is ${p:,.4g}, at or below your ${target:,} target")

# 2) Slid targets: your 78k number x (BTC now / 78k) ^ beta   (betas come from betas.json)
try:
    with open("betas.json") as f:
        meta = json.load(f)
    betas, anchor_btc = meta["betas"], meta["anchor_btc"]
except Exception as e:
    print("betas.json not usable, skipping slid targets:", e)
    betas, anchor_btc = {}, None

btc = prices.get("bitcoin", {}).get("usd")
if betas and anchor_btc and btc:
    ratio = btc / anchor_btc
    for coin, sym in SYMBOLS.items():
        tag = "s:" + coin
        anchor = TARGETS.get(coin)
        p = prices.get(coin, {}).get("usd")
        if anchor is None or sym not in betas or p is None:
            if tag in fired:
                now.add(tag)
            continue
        beta = max(betas[sym], FLOOR)
        slid = anchor * ratio ** beta
        print(sym, f"price {p:,.4g} slid target {slid:,.4g} (note {anchor:,.4g}, beta {beta:.2f})")
        if p <= slid:
            now.add(tag)
            if tag not in fired:
                notify(f"{sym} under slid target",
                       f"{sym} is ${p:,.4g}, under its slid target ${slid:,.4g}. "
                       f"Your note ${anchor:,.4g}, BTC ${btc:,.0f}, beta {beta:.1f}x")
else:
    # keep existing slid states so a temporary problem does not cause repeat pings
    now |= {t for t in fired if t.startswith("s:")}

if now != fired:
    with open(STATE, "w") as f:
        json.dump(sorted(now), f)

