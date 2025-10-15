from sqlalchemy import create_engine, String, Float, Date, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from datetime import date

# --- Database setup ---
engine = create_engine("sqlite:///finance.db", echo=False, future=True)

class Base(DeclarativeBase):
    pass

# --- Transactions table ---
class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date)
    description: Mapped[str] = mapped_column(Text)
    amount: Mapped[float] = mapped_column(Float)
    category: Mapped[str] = mapped_column(String(50))
    type: Mapped[str] = mapped_column(String(20))  # ✅ New column — "Income" or "Expense"

# --- Budget table ---
from sqlalchemy import Column

class Budget(Base):
    __tablename__ = "budget"
    category = Column(String, primary_key=True)
    limit_amount = Column(Float)

# --- Create tables ---
Base.metadata.create_all(bind=engine)

# --- Session ---
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
