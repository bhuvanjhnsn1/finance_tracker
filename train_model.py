import pandas as pd, joblib
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

df = pd.read_csv("seed_transactions.csv")
pipe = Pipeline([
    ("tfidf", TfidfVectorizer()),
    ("clf", LogisticRegression(max_iter=300))
])
pipe.fit(df["description"], df["category"])
joblib.dump(pipe, "category_model.joblib")
print("Saved category_model.joblib")
