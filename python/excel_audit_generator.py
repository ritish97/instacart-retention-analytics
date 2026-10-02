"""Builds excel/excel_data_audit.xlsx (sample, data-quality audit, day-of-week summary)."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR, EXCEL_DIR = ROOT / "data", ROOT / "excel"
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]  # order_dow: 0 = Monday


def generate_excel_audit():
    orders = pd.read_csv(DATA_DIR / "orders.csv", parse_dates=["order_date"])
    EXCEL_DIR.mkdir(exist_ok=True)

    raw_sample = orders.head(100)

    rows = []
    for col in orders.columns:
        lo, hi = orders[col].min(), orders[col].max()
        if pd.api.types.is_datetime64_any_dtype(orders[col]):
            lo, hi = lo.date().isoformat(), hi.date().isoformat()
        rows.append({"Column": col, "Data Type": str(orders[col].dtype),
                     "Missing Values": int(orders[col].isna().sum()),
                     "Min Value": lo, "Max Value": hi, "Unique Values": int(orders[col].nunique())})
    audit = pd.DataFrame(rows)

    pivot = orders.groupby("order_dow").agg(total_orders=("order_id", "count"),
                                            avg_days_since_prior=("days_since_prior_order", "mean")).reset_index()
    pivot.insert(1, "day_name", pivot["order_dow"].map(dict(enumerate(DAY_NAMES))))

    path = EXCEL_DIR / "excel_data_audit.xlsx"
    with pd.ExcelWriter(path, engine="xlsxwriter", datetime_format="yyyy-mm-dd") as writer:
        header = writer.book.add_format({"bold": True, "bg_color": "#D7E4BC", "border": 1})
        for name, df in [("Raw_Sample", raw_sample), ("Data_Quality_Audit", audit), ("Pivot_Summary", pivot)]:
            df.to_excel(writer, sheet_name=name, index=False)
            ws = writer.sheets[name]
            for i, c in enumerate(df.columns):
                ws.write(0, i, c, header)
            ws.set_column(0, len(df.columns) - 1, 18)
    print(f"Excel audit file generated at: {path}")


if __name__ == "__main__":
    generate_excel_audit()
