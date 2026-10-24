import json
import os
import urllib.request

TOPIC = os.environ["NTFY_TOPIC"]
TARGETS = json.loads(os.environ["TARGETS"])
STATE = "state.json"


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


ids = ",".join(TARGETS)
prices = get(f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd")

try:
    with open(STATE) as f:
        fired = set(json.load(f))
except Exception:
    fired = set()

now_below = set()
for coin, target in TARGETS.items():
    p = prices.get(coin, {}).get("usd")
    if p is None:
        print("no price for", coin)
        if coin in fired:
            now_below.add(coin)
        continue
    print(coin, p, "target", target)
    if p <= target:
        now_below.add(coin)
        if coin not in fired:
            notify(f"{coin} hit your target", f"{coin} is ${p:,.4g}, at or below your ${target:,} target")

if now_below != fired:
    with open(STATE, "w") as f:
        json.dump(sorted(now_below), f)
