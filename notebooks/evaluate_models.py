"""
Reproducible evaluation of the trained ML artifacts.

Loads the serialized pipelines (no retraining) and scores them on the SAME
held-out test split the training notebooks used (test_size=0.2,
random_state=42). Run from the project root:

    .venv\\Scripts\\python.exe notebooks\\evaluate_models.py

The numbers printed here are the ones documented in docs/architecture.md §4.
"""

import os
import sys

# Allow running as `python notebooks/evaluate_models.py` from the project root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

# Reuse the project's loader so the custom transformers resolve correctly
# (the pipelines were pickled with classes under the '__main__' module).
from app.services.ml.predictor import (
    FraudPredictor_instance,
    PurchasePredictor_instance,
)


def evaluate_fraud() -> None:
    print("=" * 60)
    print("FRAUD DETECTION — Binary Classification (held-out test set)")
    print("=" * 60)

    df = pd.read_csv("data/fraud_dataset.csv")
    df_clean = df.drop(columns=["transaction_id", "customer_id"])
    X = df_clean.drop(columns=["fraud"])
    y = df_clean["fraud"]

    # Identical split to notebooks/01_fraud_model_training.ipynb
    _, X_test, _, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = FraudPredictor_instance.model
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    print(f"\nTest set size: {len(y_test)} transactions "
          f"({int(y_test.sum())} fraud / {int((y_test == 0).sum())} legit)")
    print("\n--- Classification Report ---")
    print(classification_report(y_test, y_pred, digits=3))
    print("--- Confusion Matrix [rows=actual, cols=predicted] ---")
    print(confusion_matrix(y_test, y_pred))
    print("\n--- Headline metrics ---")
    print(f"Accuracy : {accuracy_score(y_test, y_pred):.3f}")
    print(f"Precision: {precision_score(y_test, y_pred):.3f}")
    print(f"Recall   : {recall_score(y_test, y_pred):.3f}")
    print(f"F1       : {f1_score(y_test, y_pred):.3f}")
    print(f"ROC-AUC  : {roc_auc_score(y_test, y_proba):.3f}")


def evaluate_purchase() -> None:
    print("\n" + "=" * 60)
    print("PURCHASE AMOUNT — Regression (held-out test set)")
    print("=" * 60)

    df = pd.read_csv("data/product_purchase_dataset.csv")
    X = df.drop(columns=["customer_id", "purchase_amount"])
    y = df["purchase_amount"]

    # Identical split to notebooks/02_purchase_model_training.ipynb
    _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = PurchasePredictor_instance.model
    y_pred = model.predict(X_test)

    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    print(f"\nTest set size: {len(y_test)} customers")
    print(f"Target range : ${y_test.min():.2f} – ${y_test.max():.2f} "
          f"(mean ${y_test.mean():.2f})")
    print("\n--- Metrics on Test Set ---")
    print(f"MAE      : ${mae:.2f}")
    print(f"RMSE     : ${rmse:.2f}")
    print(f"R^2      : {r2:.3f}")


if __name__ == "__main__":
    evaluate_fraud()
    evaluate_purchase()
