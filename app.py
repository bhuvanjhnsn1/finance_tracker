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

st.subheader("💰 Set Budget Limits")

with st.form("budget_form"):
    b1, b2 = st.columns([2, 1])
    with b1: category = st.text_input("Category")
    with b2: limit_amount = st.number_input("Budget Limit (₹)", min_value=0.0)
    save_budget = st.form_submit_button("Save Budget")

    if save_budget and category:
        with Session(session.bind) as s:
            from db import Budget
            budget = Budget(category=category, limit_amount=limit_amount)
            s.merge(budget)  # replaces or inserts
            s.commit()
        st.success(f"Budget for '{category}' set to ₹{limit_amount:.2f}")

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

# --- Budget check ---
from db import Budget

# Save last used category in Streamlit session
if "last_category" not in st.session_state:
    st.session_state.last_category = None

# Update it when a new transaction is added
if "cat_final" in locals():
    st.session_state.last_category = cat_final

# Only check budget if a category has been added before
if st.session_state.last_category:
    with Session(session.bind) as s:
        budget = s.get(Budget, st.session_state.last_category)
        if budget:
            spent = (
                s.query(Transaction)
                .filter(Transaction.category == st.session_state.last_category)
                .with_entities(Transaction.amount.label("amt"))
                .all()
            )
            total_spent = sum([x.amt for x in spent])
            if total_spent > budget.limit_amount:
                st.warning(
                    f"⚠️ Budget exceeded for '{st.session_state.last_category}'! "
                    f"(₹{total_spent:,.0f} / ₹{budget.limit_amount:,.0f})"
                )


# --- Read all transactions ---
# --- Read all transactions ---
with Session(session.bind) as s:
    df = pd.read_sql(select(Transaction), s.bind)

if df.empty:
    st.info("No transactions yet — add one above.")
    st.stop()

# --- Apply Filters ---
st.sidebar.header("Filters")

# --- Date range filter (fixed) ---
min_date = pd.to_datetime(df["date"]).min()
max_date = pd.to_datetime(df["date"]).max()

date_range = st.sidebar.date_input(
    "Select Date Range",
    (min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Unpack safely
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date


# Category filter
categories = ["All"] + sorted(df["category"].unique().tolist())
selected_cat = st.sidebar.selectbox("Filter by Category", categories)

# Filter logic
mask = (df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))
if selected_cat != "All":
    mask &= (df["category"] == selected_cat)

df_filtered = df[mask]

# --- KPIs ---
df_filtered["month"] = pd.to_datetime(df_filtered["date"]).dt.to_period("M").astype(str)
m_latest = df_filtered["month"].max()
m_total = df_filtered.loc[df_filtered["month"]==m_latest, "amount"].sum() if not df_filtered.empty else 0
k1, k2, k3 = st.columns(3)
k1.metric("This month", f"₹{m_total:,.0f}")
k2.metric("Transactions", f"{len(df_filtered)}")
k3.metric("Categories", f"{df_filtered['category'].nunique()}")

if m_total > monthly_budget:
    st.warning(f"Budget exceeded by ₹{m_total - monthly_budget:,.0f} in {m_latest}")

# --- Summary Insights ---
st.subheader("📊 Spending Insights")

if not df_filtered.empty:
    by_cat = df_filtered.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
    top3 = by_cat.head(3)
    if not top3.empty:
        st.markdown("### 🥇 Top 3 Spending Categories")
        for i, row in top3.iterrows():
            st.write(f"- **{row['category']}** — ₹{row['amount']:,.0f}")
else:
    st.info("No transactions for the selected filters.")

# --- Charts ---
c1, c2 = st.columns(2)
with c1:
    if not df_filtered.empty:
        fig1 = px.pie(by_cat, names="category", values="amount", title="Spending by Category")
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.write("No data for chart.")
with c2:
    if not df_filtered.empty:
        by_month = df_filtered.groupby("month", as_index=False)["amount"].sum()
        fig2 = px.bar(by_month, x="month", y="amount", title="Monthly Spend Trend")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.write("No data for chart.")

# --- Table + export ---
st.subheader("All Transactions")
st.dataframe(df_filtered.sort_values("date", ascending=False), use_container_width=True)
st.download_button("⬇️ Export CSV", df_filtered.to_csv(index=False).encode("utf-8"), "transactions.csv", "text/csv")
