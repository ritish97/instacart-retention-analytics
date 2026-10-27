from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SNAPSHOT = pd.Timestamp("2026-06-30") 
# share of users | orders per user | base gap (days) | gap growth per order | days before snapshot of last order
ARCHETYPES = {
    "loyal":      dict(share=.25, orders=(12, 30), gap=(4, 8),   growth=0.00, recency=(1, 10),   items=9,  reorder=.60, hours="evening"),
    "at_risk":    dict(share=.22, orders=(10, 25), gap=(5, 9),   growth=0.12, recency=(25, 60),  items=10, reorder=.45, hours="evening"),
    "churned":    dict(share=.22, orders=(1, 6),   gap=(10, 22), growth=0.00, recency=(45, 150), items=5,  reorder=.25, hours="midday"),
    "occasional": dict(share=.31, orders=(1, 6),   gap=(12, 25), growth=0.00, recency=(1, 20),   items=6,  reorder=.30, hours="midday"),
}
HOUR_W = {
    "evening": [1,1,1,1,1,1,2,3,4,4,4,4,4,4,4,5,7,10,12,12,10,6,3,2],
    "midday":  [1,1,1,1,1,1,2,3,5,7,9,10,10,9,7,5,4,4,4,3,3,2,2,1],
}
HOUR_P = {k: np.array(v) / sum(v) for k, v in HOUR_W.items()}
POP = 1 / np.arange(1, 1000) ** 0.7  # a few products are much more popular
POP /= POP.sum()


def build_dates(n, p, rng):
    """Order dates for one user; gaps capped at 30 days; ~45% nudged onto weekends."""
    base = rng.integers(p["gap"][0], p["gap"][1] + 1)
    dates = [pd.Timestamp("2025-01-06") + pd.Timedelta(days=int(rng.integers(0, 7)))]
    for i in range(n - 1):
        g = int(np.clip(round(base * (1 + p["growth"] * i) + rng.normal(0, 1.5)), 1, 30))
        if rng.random() < 0.45:
            weekend = [x for x in (g - 1, g, g + 1)
                       if 1 <= x <= 30 and (dates[-1] + pd.Timedelta(days=x)).weekday() >= 5]
            if weekend:
                g = weekend[rng.integers(len(weekend))]
        dates.append(dates[-1] + pd.Timedelta(days=g))
    # shift the whole history by whole weeks so weekdays are preserved
    target = SNAPSHOT - pd.Timedelta(days=int(rng.integers(p["recency"][0], p["recency"][1] + 1)))
    shift = 7 * round((target - dates[-1]).days / 7)
    if dates[-1] + pd.Timedelta(days=shift) > SNAPSHOT:
        shift -= 7
    return [d + pd.Timedelta(days=shift) for d in dates]

def generate_data(num_users=500):
    rng = np.random.default_rng(42)
    names = list(ARCHETYPES)
    kinds = rng.choice(names, size=num_users, p=[ARCHETYPES[k]["share"] for k in names])
    orders, items, order_id = [], [], 1

    for user_id, kind in enumerate(kinds, start=1):
        p = ARCHETYPES[kind]
        n = int(rng.integers(p["orders"][0], p["orders"][1] + 1))
        dates = build_dates(n, p, rng)
        for k, d in enumerate(dates, start=1):
            orders.append({
                "order_id": order_id, "user_id": user_id, "order_number": k,
                "order_date": d.date().isoformat(), "order_dow": d.weekday(),
                "order_hour_of_day": int(rng.choice(24, p=HOUR_P[p["hours"]])),
                "days_since_prior_order": np.nan if k == 1 else (d - dates[k - 2]).days,
            })
            n_items = int(np.clip(rng.poisson(p["items"]), 1, 40))
            for j, pid in enumerate(rng.choice(999, size=n_items, replace=False, p=POP) + 1, start=1):
                items.append({"order_id": order_id, "product_id": int(pid), "add_to_cart_order": j,
                              "reordered": int(k > 1 and rng.random() < p["reorder"])})
            order_id += 1

    DATA_DIR.mkdir(exist_ok=True)
    pd.DataFrame(orders).to_csv(DATA_DIR / "orders.csv", index=False)
    pd.DataFrame(items).to_csv(DATA_DIR / "order_products.csv", index=False)
    print(f"Generated {len(orders)} orders and {len(items)} order items for {num_users} users.")


if __name__ == "__main__":
    generate_data()
