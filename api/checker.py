# checker.py
import os
import re
from statistics import mean
from typing import Dict, List, Tuple

import requests

STEAM_APPID = 730  # CS2/CS:GO app ID
STEAM_CURRENCY_USD = 1
WEAR_BUCKETS: List[Tuple[float, float, str]] = [
    (0.00, 0.07, "Factory New"),
    (0.07, 0.15, "Minimal Wear"),
    (0.15, 0.38, "Field-Tested"),
    (0.38, 0.45, "Well-Worn"),
    (0.45, 1.00, "Battle-Scarred"),
]

PRICE_RE = re.compile(r"[\d,.]+")


def classify_wear(value: float) -> str:
    for low, high, name in WEAR_BUCKETS:
        if low <= value < high:
            return name
    raise ValueError("Float must be between 0.00 and 1.00 inclusive.")


def parse_steam_price(s: str | None) -> float | None:
    if not s:
        return None
    m = PRICE_RE.search(s)
    if not m:
        return None
    return float(m.group(0).replace(",", ""))


def steam_price_overview(market_hash_name: str, currency: int = STEAM_CURRENCY_USD) -> Dict:
    url = "https://steamcommunity.com/market/priceoverview/"
    params = {
        "currency": currency,
        "appid": STEAM_APPID,
        "market_hash_name": market_hash_name,
    }
    rsp = requests.get(url, params=params, timeout=10)
    rsp.raise_for_status()
    data = rsp.json()
    if not data.get("success"):
        raise RuntimeError(f"Steam priceoverview returned success=false for {market_hash_name}")
    return data


def csfloat_listings(
    market_hash_name: str,
    *,
    min_float: float | None = None,
    max_float: float | None = None,
    paint_seed: int | None = None,
    limit: int = 50,
) -> List[Dict]:
    api_key = os.getenv("CSFLOAT_API_KEY")
    if not api_key:
        print(
            "[warn] CSFLOAT_API_KEY not set – skipping float-specific pricing and "
            "falling back to Steam median/lowest price."
        )
        return []

    url = "https://csfloat.com/api/v1/listings"
    params: Dict[str, str | int | float] = {
        "market_hash_name": market_hash_name,
        "sort_by": "lowest_price",
        "limit": limit,
    }
    if min_float is not None:
        params["min_float"] = min_float
    if max_float is not None:
        params["max_float"] = max_float
    if paint_seed is not None:
        params["paint_seed"] = paint_seed

    headers = {"Authorization": api_key}
    rsp = requests.get(url, params=params, headers=headers, timeout=10)
    rsp.raise_for_status()
    return rsp.json()


def estimate_expected_price(args: Dict) -> Dict:
    """args = {'item': str, 'wear': str | None, 'float': float | None, 'paint_seed': int | None}"""
    if args.get("wear"):
        wear_name = args["wear"]
    elif args.get("float") is not None:
        wear_name = classify_wear(args["float"])
    else:
        wear_name = "Factory New"

    market_hash_name = f"{args['item']} ({wear_name})"

    steam = steam_price_overview(market_hash_name)
    lowest_price = parse_steam_price(steam.get("lowest_price"))
    median_price = parse_steam_price(steam.get("median_price"))

    float_avg_usd: float | None = None
    if args.get("float") is not None:
        window = 0.002
        listings = csfloat_listings(
            market_hash_name,
            min_float=max(args["float"] - window, 0),
            max_float=min(args["float"] + window, 1),
            paint_seed=args.get("paint_seed"),
        )
        prices_usd = [l["price"] / 100 for l in listings]
        if prices_usd:
            float_avg_usd = mean(prices_usd)

    # Choose: float-specific → median → lowest
    for candidate in (float_avg_usd, median_price, lowest_price):
        if candidate is not None:
            return {
                "expected_price": candidate,
                "steam_lowest": lowest_price,
                "steam_median": median_price,
                "float_adjusted": float_avg_usd,
            }

    raise RuntimeError("Could not obtain any price for the specified item.")

def estimate_across_wears(item: str) -> Dict:
    wears = ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"]
    results = []
    for wear in wears:
        try:
            p = estimate_expected_price({"item": item, "wear": wear})
            results.append({"wear": wear, "price": p["expected_price"]})
        except Exception:
            pass  # If a wear bucket doesn't exist, skip it
    if not results:
        raise RuntimeError(f"No valid prices found for any wear for {item}")
    avg = mean([x["price"] for x in results])
    return {
        "all_wears": results,
        "average_price": avg
    }
