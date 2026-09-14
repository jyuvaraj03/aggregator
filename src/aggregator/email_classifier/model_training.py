import pandas as pd
import numpy as np

import joblib

from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from sklearn.model_selection import (
    train_test_split,
    StratifiedKFold,
    cross_validate,
)

from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    average_precision_score,
)

RANDOM_STATE = 42

df = pd.read_csv("data/labelled_samples.csv")

df["body"] = df["body"].fillna("").astype(str)

df["is_transaction_alert"] = df["is_transaction_alert"].astype(float)

X = df["body"]
y = df["is_transaction_alert"]

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=RANDOM_STATE,
    stratify=y,
)

print("Split:")
print(f"Train: {len(X_train)} samples, Test: {len(X_test)} samples")

# Feature extraction

features = FeatureUnion(
    [
        (
            "word",
            TfidfVectorizer(
                analyzer="word",
                ngram_range=(1, 2),
                min_df=2,
                max_df=0.98,
                max_features=12_000,
                sublinear_tf=True,
                strip_accents="unicode",
                lowercase=True,
            ),
        ),
        (
            "char",
            TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(3, 5),
                min_df=2,
                max_features=15_000,
                sublinear_tf=True,
                lowercase=True,
            ),
        ),
    ]
)

# Classification

classifier = LogisticRegression(
    C=0.3,
    class_weight="balanced",
    max_iter=2000,
    random_state=RANDOM_STATE,
)

# Whole pipeline
model = Pipeline(
    [
        ("features", features),
        ("classifier", classifier),
    ]
)

# Cross-validation
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
scoring = {
    "precision": "precision",
    "recall": "recall",
    "f1": "f1",
    "roc_auc": "roc_auc",
    "average_precision": "average_precision",
}

scores = cross_validate(
    model,
    X_train,
    y_train,
    cv=cv,
    scoring=scoring,
    n_jobs=-1
)


print("Cross-validation results:")

for metric in scoring:
    values = scores[f"test_{metric}"]

    print(
        f"{metric:20s}: "
        f"{values.mean():.3f} "
        f"+/- {values.std():.3f}"
    )


# Train the model on the full training set
model.fit(X_train, y_train)

# Evaluate on the test set
predictions = model.predict(X_test)

probabilities = model.predict_proba(X_test)[:, 1]

print("Final evaluation on the test set:")

print(classification_report(y_test, predictions, digits=3))

print("Confusion Matrix:")
print(confusion_matrix(y_test, predictions))

roc_auc = round(roc_auc_score(y_test, probabilities), 3)
print(f"ROC AUC: {roc_auc}")

print(f"Average Precision: {round(average_precision_score(y_test, probabilities), 3)}")

# Save the model
joblib.dump(model, "transaction_alert_classifier.joblib")

print("Model saved to transaction_alert_classifier.joblib")


negative_probs = probabilities[y_test.to_numpy() == 0]
positive_probs = probabilities[y_test.to_numpy() == 1]

print(
    "Highest negative probability:",
    negative_probs.max()
)

print(
    "Lowest positive probability:",
    positive_probs.min()
)

results = pd.DataFrame({
    "body": X_test.to_numpy(),
    "actual": y_test.to_numpy(),
    "probability": probabilities,
})

print("\nMost transaction-like negatives:")
print(
    results[results["actual"] == 0]
    .sort_values("probability", ascending=False)
    [["probability", "body"]]
    .head(10)
    .to_string(index=False)
)

print("\nLeast transaction-like positives:")
print(
    results[results["actual"] == 1]
    .sort_values("probability")
    [["probability", "body"]]
    .head(10)
    .to_string(index=False)
)


feature_names = (
    model.named_steps["features"]
    .get_feature_names_out()
)

coefficients = (
    model.named_steps["classifier"]
    .coef_[0]
)

top_positive = np.argsort(coefficients)[-50:][::-1]
top_negative = np.argsort(coefficients)[:50]

print("\nTOP TRANSACTION FEATURES\n")

for i in top_positive:
    print(
        f"{feature_names[i]:45s}"
        f"{coefficients[i]:8.3f}"
    )

print("\nTOP NON-TRANSACTION FEATURES\n")

for i in top_negative:
    print(
        f"{feature_names[i]:45s}"
        f"{coefficients[i]:8.3f}"
    )
