import streamlit as st
import pandas as pd
from datetime import date
import joblib
from sqlalchemy.orm import Session
from db import SessionLocal, Transaction, Budget
from sqlalchemy import select
import plotly.express as px

st.set_page_config(page_title="Personal Finance Tracker", page_icon="💸", layout="wide")

# --- Cached resources ---
@st.cache_resource
def get_session():
    return SessionLocal()

@st.cache_resource
def load_model():
    return joblib.load("category_model.joblib")

session = get_session()
model = load_model()

# --- Sidebar ---
st.sidebar.header("💰 Budget & Filters")
monthly_budget = st.sidebar.number_input("Monthly budget (₹)", min_value=0, value=20000, step=500)
st.sidebar.caption("Tip: Adjust to see alerts on overspending.")

# --- App title ---
st.title("💸 Personal Finance Tracker (AI-assisted)")

# --- Budget setup form ---
st.subheader("💰 Set Budget Limits")
with st.form("budget_form"):
    b1, b2 = st.columns([2, 1])
    with b1:
        category = st.text_input("Category")
    with b2:
        limit_amount = st.number_input("Budget Limit (₹)", min_value=0.0)
    save_budget = st.form_submit_button("Save Budget")

    if save_budget and category:
        with Session(session.bind) as s:
            budget = Budget(category=category, limit_amount=limit_amount)
            s.merge(budget)
            s.commit()
        st.success(f"Budget for '{category}' set to ₹{limit_amount:,.2f}")

# --- Add transaction form ---
with st.form("add_txn", clear_on_submit=True):
    c1, c2, c3, c4, c5 = st.columns([1, 2, 1, 1, 1])
    with c1:
        d = st.date_input("Date", value=date.today())
    with c2:
        desc = st.text_input("Description", placeholder="e.g., Salary, Pizza, Uber, Rent")
    with c3:
        amt = st.number_input("Amount", min_value=0.0, step=10.0)
    with c4:
        txn_type = st.selectbox("Type", ["Expense", "Income"])
    with c5:
        cat = st.selectbox(
            "Category (or AI)",
            ["(AI) auto-predict", "Food", "Groceries", "Rent", "Utilities", "Entertainment",
             "Travel", "Transport", "Shopping", "Health", "Salary", "Freelance", "Other"]
        )

    submitted = st.form_submit_button("Add")
    if submitted and desc and amt > 0:
        if cat == "(AI) auto-predict":
            cat_final = model.predict([desc])[0]
        else:
            cat_final = cat

        txn = Transaction(date=d, description=desc, amount=float(amt), category=cat_final, type=txn_type)
        with Session(session.bind) as s:
            s.add(txn)
            s.commit()
        st.success(f"Added: {desc} | ₹{amt:.2f} | {txn_type} | {cat_final}")

# --- Load all transactions ---
with Session(session.bind) as s:
    df = pd.read_sql(select(Transaction), s.bind)

if df.empty:
    st.info("No transactions yet — add one above.")
    st.stop()

# --- Convert datatypes safely ---
df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["type"] = df["type"].fillna("Expense")

# --- Sidebar Filters ---
st.sidebar.subheader("Filters")

min_date = df["date"].min()
max_date = df["date"].max()

date_range = st.sidebar.date_input(
    "Select Date Range",
    (min_date, max_date),
    min_value=min_date,
    max_value=max_date
)
start_date, end_date = date_range if isinstance(date_range, tuple) else (min_date, max_date)

categories = ["All"] + sorted(df["category"].unique().tolist())
selected_cat = st.sidebar.selectbox("Filter by Category", categories)

mask = (df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))
if selected_cat != "All":
    mask &= (df["category"] == selected_cat)
df_filtered = df.loc[mask]

if df_filtered.empty:
    st.warning("⚠️ No transactions found for the selected date range or category.")
    st.stop()

# --- Financial Summary ---
st.subheader("📊 Financial Summary")

total_income = df_filtered.loc[df_filtered["type"] == "Income", "amount"].sum()
total_expense = df_filtered.loc[df_filtered["type"] == "Expense", "amount"].sum()
net_balance = total_income - total_expense

c1, c2, c3 = st.columns(3)
c1.metric("Total Income", f"₹{total_income:,.0f}")
c2.metric("Total Expense", f"₹{total_expense:,.0f}")
c3.metric("Net Balance", f"₹{net_balance:,.0f}")

# --- Budget Warning ---
latest_month = pd.to_datetime(df_filtered["date"]).dt.to_period("M").max()
this_month_expense = df_filtered.loc[
    (pd.to_datetime(df_filtered["date"]).dt.to_period("M") == latest_month)
    & (df_filtered["type"] == "Expense"),
    "amount"
].sum()

if this_month_expense > monthly_budget:
    st.warning(f"⚠️ Budget exceeded by ₹{this_month_expense - monthly_budget:,.0f} in {latest_month}")

# --- Spending Insights ---
st.subheader("💡 Spending Insights")

by_cat = (
    df_filtered[df_filtered["type"] == "Expense"]
    .groupby("category", as_index=False)["amount"]
    .sum()
    .sort_values("amount", ascending=False)
)
if not by_cat.empty:
    st.markdown("### 🥇 Top 3 Spending Categories")
    for i, row in by_cat.head(3).iterrows():
        st.write(f"- **{row['category']}** — ₹{row['amount']:,.0f}")

# --- Charts ---
c1, c2 = st.columns(2)
with c1:
    if not by_cat.empty:
        fig1 = px.pie(by_cat, names="category", values="amount", title="Spending by Category")
        st.plotly_chart(fig1, use_container_width=True)
with c2:
    by_month = (
        df_filtered.groupby([pd.to_datetime(df_filtered["date"]).dt.to_period("M"), "type"], as_index=False)["amount"]
        .sum()
    )
    by_month["month"] = by_month["date"].astype(str)
    fig2 = px.bar(by_month, x="month", y="amount", color="type", barmode="group",
                  title="Monthly Income vs Expense Trend")
    st.plotly_chart(fig2, use_container_width=True)

# --- Transactions Table ---
st.subheader("📋 All Transactions")
st.dataframe(df_filtered.sort_values("date", ascending=False), use_container_width=True)
st.download_button(
    "⬇️ Export CSV",
    df_filtered.to_csv(index=False).encode("utf-8"),
    "transactions.csv",
    "text/csv"
)
