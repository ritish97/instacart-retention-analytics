"""RFM & churn engine: reads data/orders.csv + data/order_products.csv,
writes data/instacart_user_segments.csv.

Recency = days from the user's LAST order to a snapshot date (latest order date + 1 day).
Users with a single order have no purchase gap, so avg_lapse is left empty for them.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


def segment_user(row):
    r, f = row["R_score"], row["F_score"]
    if r >= 3 and f >= 3:
        return "Loyal Power Users"
    if r <= 2 and f >= 3:
        return "At Risk (High Volume)"
    if r <= 2 and f <= 2:
        return "Churned / Dormant"
    return "Occasional Shoppers"


def run_rfm_pipeline():
    orders = pd.read_csv(DATA_DIR / "orders.csv", parse_dates=["order_date"])
    items = pd.read_csv(DATA_DIR / "order_products.csv")

    snapshot = orders["order_date"].max() + pd.Timedelta(days=1)

    rfm = orders.groupby("user_id").agg(
        last_order=("order_date", "max"),
        avg_lapse=("days_since_prior_order", "mean"),   # NaN for one-order users
        frequency=("order_number", "max"),
    ).reset_index()
    rfm["recency_days"] = (snapshot - rfm["last_order"]).dt.days

    items_per_order = items.groupby("order_id").size().rename("items_in_order")
    monetary = (orders.merge(items_per_order, on="order_id", how="left")
                .groupby("user_id")["items_in_order"].sum().rename("total_items_bought").reset_index())
    rfm = rfm.merge(monetary, on="user_id")
    rfm["total_items_bought"] = rfm["total_items_bought"].fillna(0).astype(int)

    # Quartile scores 1-4 (4 = best). rank(method="first") breaks ties by row order.
    rfm["R_score"] = pd.qcut(rfm["recency_days"].rank(method="first"), 4, labels=[4, 3, 2, 1]).astype(int)
    rfm["F_score"] = pd.qcut(rfm["frequency"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
    rfm["M_score"] = pd.qcut(rfm["total_items_bought"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
    rfm["Customer_Segment"] = rfm.apply(segment_user, axis=1)

    cols = ["user_id", "recency_days", "avg_lapse", "frequency", "total_items_bought",
            "R_score", "F_score", "M_score", "Customer_Segment"]
    rfm[cols].to_csv(DATA_DIR / "instacart_user_segments.csv", index=False)

    print(f"RFM pipeline complete. Snapshot date: {snapshot.date()}. Segmented {len(rfm)} users.")
    print(rfm["Customer_Segment"].value_counts())


if __name__ == "__main__":
    run_rfm_pipeline()
