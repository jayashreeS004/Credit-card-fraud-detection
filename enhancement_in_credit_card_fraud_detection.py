# -*- coding: utf-8 -*-
"""Enhancement in credit card fraud detection.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/15oU0IrfX6khm0nudtgCgiHeTZC209q5d
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import shap

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, classification_report,
    confusion_matrix, roc_auc_score, roc_curve
)
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, StackingClassifier
from sklearn.svm import SVC
from xgboost import XGBClassifier

import warnings
warnings.filterwarnings("ignore")

# 2.1 Load dataset
df = pd.read_excel("credit_card_fraud_dataset.xlsx")

# 2.2 Separate X/y
X = df.drop("Class", axis=1)
y = df["Class"]

# 2.3 Scale features
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 2.4 Train/Test split (stratified)
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, stratify=y, random_state=42
)

lr = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
lr.fit(X_train, y_train)

lr_pred  = lr.predict(X_test)
lr_probs = lr.predict_proba(X_test)[:, 1]

# 4.1 Train RF
rf = RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=42)
rf.fit(X_train, y_train)

rf_pred  = rf.predict(X_test)
rf_probs = rf.predict_proba(X_test)[:, 1]

# 4.2 Prepare DataFrame for SHAP
X_test_df = pd.DataFrame(X_test, columns=X.columns)

# 4.3 SHAP explainer & summary plot (handles new/old SHAP APIs)
explainer = shap.TreeExplainer(rf)
try:
    shap_exp = explainer(X_test_df)
    shap.summary_plot(shap_exp.values, X_test_df, show=False)
except:
    shap_vals = explainer.shap_values(X_test_df)
    # If list returned, select class‑1 values
    data_to_plot = shap_vals[1] if isinstance(shap_vals, list) else shap_vals
    shap.summary_plot(data_to_plot, X_test_df, show=False)

plt.tight_layout()
plt.show()

base_learners = [
    ("rf",  RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=42)),
    ("xgb", XGBClassifier(use_label_encoder=False, eval_metric="logloss",
                          scale_pos_weight=(y_train==0).sum()/(y_train==1).sum())),
    ("svm", SVC(probability=True, class_weight="balanced", random_state=42))
]

stack = StackingClassifier(
    estimators=base_learners,
    final_estimator=LogisticRegression(),
    passthrough=True,
    cv=5
)
stack.fit(X_train, y_train)

stack_pred  = stack.predict(X_test)
stack_probs = stack.predict_proba(X_test)[:, 1]

models = {
    "Logistic Regression": (lr_pred,   lr_probs),
    "Random Forest":       (rf_pred,   rf_probs),
    "Stacked Ensemble":    (stack_pred, stack_probs)
}

for name, (pred, probs) in models.items():
    acc = accuracy_score(y_test, pred)
    auc = roc_auc_score(y_test, probs)
    print(f"\n--- {name} ---")
    print(f"Accuracy: {acc:.2f}    AUC: {auc:.2f}")
    print(classification_report(y_test, pred, digits=2))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, pred))

plt.figure(figsize=(8,6))
for name, (_, probs) in models.items():
    fpr, tpr, _ = roc_curve(y_test, probs)
    auc = roc_auc_score(y_test, probs)
    plt.plot(fpr, tpr, label=f"{name} (AUC={auc:.2f})")

plt.plot([0,1], [0,1], "k--")
plt.xlabel("False Positive Rate")
plt.ylabel("True Positive Rate")
plt.title("ROC Curves Comparison")
plt.legend()
plt.grid(True)
plt.show()