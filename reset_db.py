from db import Base, engine, Transaction, Budget
from sqlalchemy import inspect

# Drop only the transactions table (if it exists)
inspector = inspect(engine)
if "transactions" in inspector.get_table_names():
    Transaction.__table__.drop(engine)
    print("✅ Dropped old 'transactions' table")

# Recreate all tables
Base.metadata.create_all(bind=engine)
print("✅ Recreated all tables with latest schema")
