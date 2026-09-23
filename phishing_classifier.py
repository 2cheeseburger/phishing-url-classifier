import math
import os
import re
from collections import Counter
from urllib.parse import urlparse

import matplotlib
matplotlib.use("Agg")  # lets us save plots without opening a window
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

# ---- SETTINGS: edit these to match your dataset ----
CSV_PATH = "data/urls.csv"
URL_COLUMN = "URL"
LABEL_COLUMN = "Label"
PHISHING_VALUE = "bad"   # the label value that means phishing (use "1" if labels are numbers)
SAMPLE_SIZE = 50000      # keeps feature extraction fast
# ----------------------------------------------------


def entropy(s):
    if not s:
        return 0
    counts = Counter(s)
    return -sum((c / len(s)) * math.log2(c / len(s)) for c in counts.values())


def extract_features(url):
    url = str(url)
    if not re.match(r"^\w+://", url):
        url = "http://" + url
    try:
        parsed = urlparse(url)
    except ValueError:
        parsed = urlparse("http://invalid")
    host = parsed.netloc.lower()
    return {
        "url_length": len(url),
        "host_length": len(host),
        "num_dots": host.count("."),
        "num_hyphens": host.count("-"),
        "num_digits": sum(c.isdigit() for c in url),
        "has_at": int("@" in url),
        "has_ip": int(bool(re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}(:\d+)?", host))),
        "uses_https": int(parsed.scheme == "https"),
        "path_length": len(parsed.path),
        "num_params": parsed.query.count("&") + (1 if parsed.query else 0),
        "entropy": entropy(url),
        "suspicious_words": sum(
            w in url.lower()
            for w in ["login", "verify", "secure", "account", "update", "bank"]
        ),
    }


def main():
    os.makedirs("results", exist_ok=True)

    df = pd.read_csv(CSV_PATH)
    df = df.dropna(subset=[URL_COLUMN, LABEL_COLUMN]).drop_duplicates(URL_COLUMN)
    if len(df) > SAMPLE_SIZE:
        df = df.sample(SAMPLE_SIZE, random_state=42)
    df = df.reset_index(drop=True)
    print(f"Using {len(df)} URLs")

    y = (df[LABEL_COLUMN].astype(str).str.lower() == PHISHING_VALUE.lower()).astype(int)
    print("Phishing share:", round(y.mean(), 3))

    X = pd.DataFrame([extract_features(u) for u in df[URL_COLUMN]])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y.values, test_size=0.2, stratify=y.values, random_state=42
    )

    # Baseline model
    baseline = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    baseline.fit(X_train, y_train)
    print("\n=== Baseline: Logistic Regression ===")
    print(classification_report(y_test, baseline.predict(X_test)))

    # Main model
    rf = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    pred = rf.predict(X_test)
    print("\n=== Random Forest ===")
    print(classification_report(y_test, pred))
    print("Confusion matrix (rows = actual, columns = predicted):")
    print(confusion_matrix(y_test, pred))

    # Feature importance plot
    importances = pd.Series(rf.feature_importances_, index=X.columns).sort_values()
    importances.plot(kind="barh", figsize=(8, 5))
    plt.title("Random Forest feature importance")
    plt.tight_layout()
    plt.savefig("results/feature_importance.png", dpi=150)
    print("\nSaved results/feature_importance.png")

    # Show some mistakes to study
    test_urls = df.loc[X_test.index, URL_COLUMN]
    mistakes = test_urls[pred != y_test]
    print("\nSample of misclassified URLs:")
    print(mistakes.head(15).to_string())


if __name__ == "__main__":
    main()