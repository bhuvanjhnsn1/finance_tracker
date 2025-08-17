import streamlit as st
import pandas as pd
from datetime import date
import joblib
from sqlalchemy.orm import Session
from db import SessionLocal, Transaction
from sqlalchemy import select
import plotly.express as px

st.set_page_config(page_title="Personal Finance Tracker", page_icon="💸", layout="wide")

@st.cache_resource
def get_session():
    return SessionLocal()

@st.cache_resource
def load_model():
    return joblib.load("category_model.joblib")

session = get_session()
model = load_model()

st.title("💸 Personal Finance Tracker (AI-assisted)")
with st.sidebar:
    st.header("Budget & Filters")
    monthly_budget = st.number_input("Monthly budget (₹)", min_value=0, value=20000, step=500)
    st.caption("Tip: Adjust to see alerts on overspending.")

# --- Add transaction form ---
with st.form("add_txn", clear_on_submit=True):
    c1, c2, c3, c4 = st.columns([1,2,1,1])
    with c1: d = st.date_input("Date", value=date.today())
    with c2: desc = st.text_input("Description", placeholder="e.g., pizza, uber, rent")
    with c3: amt = st.number_input("Amount", min_value=0.0, step=10.0)
    with c4: cat = st.selectbox("Category (or AI)", ["(AI) auto-predict","Food","Groceries","Rent","Utilities","Entertainment","Travel","Transport","Shopping","Health","Other"])
    submitted = st.form_submit_button("Add")
    if submitted and desc and amt > 0:
        if cat == "(AI) auto-predict":
            pred = model.predict([desc])[0]
            cat_final = pred
        else:
            cat_final = cat
        txn = Transaction(date=d, description=desc, amount=float(amt), category=cat_final)
        with Session(session.bind) as s:
            s.add(txn)
            s.commit()
        st.success(f"Added: {desc} | ₹{amt:.2f} | {cat_final}")

# --- Read all transactions ---
with Session(session.bind) as s:
    df = pd.read_sql(select(Transaction), s.bind)

if df.empty:
    st.info("No transactions yet — add one above.")
    st.stop()

# --- KPIs ---
df["month"] = pd.to_datetime(df["date"]).dt.to_period("M").astype(str)
m_latest = df["month"].max()
m_total = df.loc[df["month"]==m_latest, "amount"].sum()
k1, k2, k3 = st.columns(3)
k1.metric("This month", f"₹{m_total:,.0f}")
k2.metric("Transactions", f"{len(df)}")
k3.metric("Categories", f"{df['category'].nunique()}")

if m_total > monthly_budget:
    st.warning(f"Budget exceeded by ₹{m_total - monthly_budget:,.0f} in {m_latest}")

# --- Charts ---
c1, c2 = st.columns(2)
with c1:
    by_cat = df.groupby("category", as_index=False)["amount"].sum()
    fig1 = px.pie(by_cat, names="category", values="amount", title="Spending by Category")
    st.plotly_chart(fig1, use_container_width=True)
with c2:
    by_month = df.groupby("month", as_index=False)["amount"].sum()
    fig2 = px.bar(by_month, x="month", y="amount", title="Monthly Spend Trend")
    st.plotly_chart(fig2, use_container_width=True)

# --- Table + export ---
st.subheader("All Transactions")
st.dataframe(df.sort_values("date", ascending=False), use_container_width=True)
st.download_button("⬇️ Export CSV", df.to_csv(index=False).encode("utf-8"), "transactions.csv", "text/csv")
