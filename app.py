from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Instacart Retention Analytics", page_icon="🛒", layout="wide")

DATA = Path(__file__).parent / "data"
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]  # order_dow: 0 = Monday


@st.cache_data
def load():
    seg = pd.read_csv(DATA / "instacart_user_segments.csv")
    orders = pd.read_csv(DATA / "orders.csv")
    return seg, orders.merge(seg[["user_id", "Customer_Segment"]], on="user_id")


seg, orders = load()

# ---------- Sidebar filters ----------
st.sidebar.header("Filters")
chosen = st.sidebar.multiselect("Customer segment", sorted(seg.Customer_Segment.unique()),
                                default=sorted(seg.Customer_Segment.unique()))
f_min, f_max = int(seg.frequency.min()), int(seg.frequency.max())
freq = st.sidebar.slider("Number of orders", f_min, f_max, (f_min, f_max))

s = seg[seg.Customer_Segment.isin(chosen) & seg.frequency.between(*freq)]
o = orders[orders.user_id.isin(s.user_id)]

# ---------- KPIs ----------
st.title("🛒 Instacart Customer Retention & Churn Dashboard")
st.caption("Synthetic dataset: segments are derived from RFM quartiles. recency_days = days since the last order.")
if s.empty:
    st.warning("No users match these filters.")
    st.stop()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Users", f"{len(s):,}")
k2.metric("Dormant share", f"{(s.Customer_Segment == 'Churned / Dormant').mean():.1%}")
k3.metric("Avg orders / user", f"{s.frequency.mean():.1f}")
k4.metric("Avg items / order", f"{s.total_items_bought.sum() / s.frequency.sum():.1f}")

tab1, tab2, tab3 = st.tabs(["Segments", "Ordering behaviour", "User explorer"])

with tab1:
    c1, c2 = st.columns(2)
    counts = s.Customer_Segment.value_counts().reset_index()
    c1.plotly_chart(px.pie(counts, names="Customer_Segment", values="count", hole=0.5,
                           title="Users by segment"), width="stretch")
    c2.plotly_chart(px.scatter(s, x="recency_days", y="frequency", color="Customer_Segment",
                               hover_data=["user_id", "total_items_bought"],
                               title="Recency vs frequency"), width="stretch")
    st.dataframe(s.groupby("Customer_Segment").agg(users=("user_id", "count"),
                 avg_orders=("frequency", "mean"), avg_items=("total_items_bought", "mean"),
                 avg_recency_days=("recency_days", "mean")).round(2))

with tab2:
    heat = o.groupby(["order_dow", "order_hour_of_day"]).size().unstack(fill_value=0)
    heat.index = [DAYS[i] for i in heat.index]
    st.plotly_chart(px.imshow(heat, aspect="auto", labels=dict(x="Hour of day", y="Day", color="Orders"),
                              title="Orders by day and hour"), width="stretch")
    trend = o.groupby(["order_number", "Customer_Segment"]).days_since_prior_order.mean().reset_index()
    st.plotly_chart(px.line(trend, x="order_number", y="days_since_prior_order",
                            color="Customer_Segment", title="Avg days between orders, by order number"),
                    width="stretch")

with tab3:
    st.dataframe(s, width="stretch")
    st.download_button("Download filtered users (CSV)", s.to_csv(index=False), "filtered_users.csv")
