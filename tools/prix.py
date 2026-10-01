"""Robot des prix (GitHub Actions) — écrit prix.json à côté de l'app budget.

Pourquoi : Yahoo Finance a le VRAI prix des actifs Trade Republic (ex. Vanguard S&P 500 VUAA),
mais bloque les appels depuis une page web (CORS). Ce script tourne chez GitHub (cron), va
chercher les prix et les dépose dans le site → l'app les lit sans restriction.

Bibliothèque standard uniquement (rien à installer).
"""
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone

# id dans l'app → symbole Yahoo (cotation en EUR sur Xetra, comme Trade Republic)
ASSETS = {
    "vuaa": "VUAA.DE",  # Vanguard S&P 500 UCITS ETF USD Acc (IE00BFMXXD54)
    "nvda": "NVD.DE",   # NVIDIA en euros (Xetra)
}
# période de l'app → (plage Yahoo, intervalle)
RANGES = {"1S": ("5d", "30m"), "1M": ("1mo", "1d"), "1A": ("1y", "1d"), "Global": ("max", "1wk")}


def chart(symbol, rng, interval):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={rng}&interval={interval}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)["chart"]["result"][0]
        except Exception as e:  # 429 / réseau → on réessaie un peu plus tard
            if attempt == 2:
                raise
            print(f"  {symbol} {rng}: {e}, nouvel essai", file=sys.stderr)
            time.sleep(5 * (attempt + 1))


def series(res):
    ts = res.get("timestamp") or []
    closes = res["indicators"]["quote"][0].get("close") or []
    pts = [(t, round(c, 4)) for t, c in zip(ts, closes) if c is not None]
    return {"t": [p[0] for p in pts], "p": [p[1] for p in pts]}


def main():
    out = {"updated": int(time.time()), "assets": {}}
    for aid, sym in ASSETS.items():
        day = chart(sym, "1d", "1h")
        meta = day["meta"]
        price, prev = meta["regularMarketPrice"], meta.get("chartPreviousClose") or meta.get("previousClose")
        asset = {
            "symbol": sym,
            "currency": meta.get("currency"),
            "price": round(price, 4),
            "changePct24h": round((price / prev - 1) * 100, 3) if prev else 0,
            "marketTime": meta.get("regularMarketTime"),
            "history": {},
        }
        for tf, (rng, itv) in RANGES.items():
            asset["history"][tf] = series(chart(sym, rng, itv))
        out["assets"][aid] = asset
        print(f"{aid}: {price} {meta.get('currency')} ({asset['changePct24h']:+.2f} %)")
    with open("prix.json", "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"))
    print("prix.json écrit", datetime.now(timezone.utc).isoformat(timespec="seconds"))


if __name__ == "__main__":
    main()
