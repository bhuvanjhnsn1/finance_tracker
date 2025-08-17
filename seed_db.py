import pandas as pd
from datetime import date
from sqlalchemy.orm import Session
from db import SessionLocal, Transaction

df = pd.read_csv("seed_transactions.csv")
with Session(SessionLocal().bind) as s:
    for _, r in df.iterrows():
        s.add(Transaction(date=date.today(), description=r["description"], amount=float(r["amount"]), category=r["category"]))
    s.commit()
print("Seeded DB.")
