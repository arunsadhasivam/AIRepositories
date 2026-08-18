"""
Twitter Bot Detector — Complete Pipeline, Step-by-Step Functions
Algorithms included: Logistic Regression, Random Forest, XGBoost,
LightGBM, SVM, Neural Network (MLP)

Run each function independently, or run main() to execute the full pipeline.
"""

import pandas as pd                                              # data loading & manipulation
import numpy as np                                                 # numerical operations
from sklearn.model_selection import train_test_split                # train/test split
from sklearn.preprocessing import StandardScaler                     # feature scaling
from sklearn.feature_extraction.text import TfidfVectorizer           # tweet text -> numeric features
from sklearn.metrics import classification_report, roc_auc_score       # evaluation

from sklearn.linear_model import LogisticRegression                   # Algorithm 1
from sklearn.ensemble import RandomForestClassifier                    # Algorithm 2
from xgboost import XGBClassifier                                       # Algorithm 3
from lightgbm import LGBMClassifier                                      # Algorithm 4
from sklearn.svm import LinearSVC                                         # Algorithm 5 (linear SVM, scales well)
from sklearn.calibration import CalibratedClassifierCV                     # wraps SVM to get probability scores
from sklearn.neural_network import MLPClassifier                            # Algorithm 6 (Neural Network)

DATA_PATH = "/mnt/user-data/uploads/bot_detection_data.csv"


# =================================================================
# STEP 1: Load Data
# =================================================================
def load_data(path=DATA_PATH):
    """Load the CSV into a pandas DataFrame."""
    df = pd.read_csv(path)
    print(f"[load_data] Loaded shape: {df.shape}")
    print(f"[load_data] Label distribution:\n{df['Bot Label'].value_counts()}")
    return df


# =================================================================
# STEP 2: Feature Engineering (numeric signals from raw columns)
# =================================================================
def engineer_features(df):
    """Create numeric features from raw columns. Returns modified df."""
    df = df.copy()                                                  # avoid mutating original

    df["Verified"] = df["Verified"].astype(int)                       # bool -> 0/1

    df["Hashtags"] = df["Hashtags"].fillna("")                         # handle missing hashtags
    df["Hashtag_Count"] = df["Hashtags"].apply(lambda x: len(x.split()) if x else 0)

    df["Tweet_Length"] = df["Tweet"].apply(len)                          # length of tweet text

    df["Created At"] = pd.to_datetime(df["Created At"])                   # parse datetime
    df["Post_Hour"] = df["Created At"].dt.hour                              # extract hour posted

    # engagement ratio: retweets relative to followers (+1 avoids divide-by-zero)
    df["Retweet_Per_Follower"] = df["Retweet Count"] / (df["Follower Count"] + 1)

    print("[engineer_features] Added: Hashtag_Count, Tweet_Length, Post_Hour, Retweet_Per_Follower")
    return df


# =================================================================
# STEP 3: Build Feature Matrix (numeric + TF-IDF text combined)
# WHY TF-IDF HERE: models can't read raw text directly -- TF-IDF
# converts each tweet into a vector of word-importance scores (a word
# is weighted high if it's frequent in THIS tweet but rare across ALL
# tweets). This lets repetitive/templated bot language show up as a
# distinct numeric pattern the model can learn from, without needing
# a full language model.
# =================================================================
def build_feature_matrix(df, max_tfidf_features=100):
    """
    Combines numeric features with TF-IDF vectorized tweet text.
    Returns X (features), y (labels), and the fitted tfidf vectorizer
    (needed later to transform new/unseen tweets the same way).
    """
    numeric_features = [
        "Retweet Count", "Mention Count", "Follower Count", "Verified",
        "Hashtag_Count", "Tweet_Length", "Post_Hour", "Retweet_Per_Follower",
    ]
    X_numeric = df[numeric_features].values

    tfidf = TfidfVectorizer(max_features=max_tfidf_features, stop_words="english")
    X_text = tfidf.fit_transform(df["Tweet"]).toarray()

    X = np.hstack([X_numeric, X_text])                                   # combine side by side
    y = df["Bot Label"].values

    feature_names = numeric_features + [f"tfidf_{w}" for w in tfidf.get_feature_names_out()]

    print(f"[build_feature_matrix] X shape: {X.shape}, y shape: {y.shape}")
    return X, y, tfidf, feature_names


# =================================================================
# STEP 4: Train/Test Split
# =================================================================
def split_data(X, y, test_size=0.2):
    """Stratified split keeps the 50/50 class balance in both sets."""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )
    print(f"[split_data] Train: {X_train.shape}, Test: {X_test.shape}")
    return X_train, X_test, y_train, y_test


# =================================================================
# STEP 5: Feature Scaling (needed for Logistic Regression, SVM, MLP)
# WHY SCALING: Follower Count can be in the thousands while Verified
# is just 0/1 -- without scaling, large-magnitude features would
# dominate distance/gradient-based math in LR, SVM, and MLP, even if
# they aren't actually more important. Tree-based models (RF, XGBoost,
# LightGBM) split on raw thresholds per feature, so they don't need
# this step -- that's why scaling is applied selectively, not globally.
# =================================================================
def scale_features(X_train, X_test):
    """Fit scaler on train only, apply to both -- prevents data leakage."""
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    print("[scale_features] Scaling complete")
    return X_train_scaled, X_test_scaled, scaler


# =================================================================
# STEP 6: Evaluation Helper (reused by every model)
# =================================================================
def evaluate_model(name, model, X_test, y_test, use_decision_function=False):
    """Prints classification report + ROC-AUC for any trained model."""
    y_pred = model.predict(X_test)

    if use_decision_function:
        # LinearSVC has no predict_proba by default -- use decision_function instead
        y_score = model.decision_function(X_test)
    else:
        y_score = model.predict_proba(X_test)[:, 1]                        # probability of "bot"

    print(f"\n=== {name} ===")
    print(classification_report(y_test, y_pred, target_names=["human", "bot"]))
    print(f"ROC-AUC: {roc_auc_score(y_test, y_score):.3f}")
    return y_pred, y_score


# =================================================================
# ALGORITHM 1: Logistic Regression
# WHY THIS ALGORITHM:
# - Our features (Retweet Count, Follower Count, Tweet_Length, etc.) are
#   tabular/engineered numbers, not raw sequences -- Logistic Regression
#   is the right FIRST model to try on this kind of data.
# - It directly outputs a probability (0-1) via a sigmoid function --
#   matches our need for a "confidence score" (>0.7 bot, <0.3 human).
# - It's fast to train and easy to explain ("Follower Count has this much
#   weight") -- important for interpretability/audit in bot detection.
# - Used as the BASELINE: if a more complex model doesn't beat this,
#   the complexity isn't worth it.
# =================================================================
def train_logistic_regression(X_train, y_train):
    """Baseline linear model. Fast, interpretable, good starting point."""
    model = LogisticRegression(max_iter=1000)                                # max_iter raised so it fully converges
    model.fit(X_train, y_train)
    print("[train_logistic_regression] Training complete")
    return model


# =================================================================
# ALGORITHM 2: Random Forest
# WHY THIS ALGORITHM:
# - Logistic Regression assumes a roughly LINEAR relationship between
#   features and the bot/human outcome. Real bot signals are often
#   NON-LINEAR interactions (e.g. "high retweets is only suspicious IF
#   follower count is also low") -- a single straight-line boundary
#   can't capture that, but a tree split can.
# - Random Forest builds many decision trees on random subsets of data
#   and features, then averages their votes -- reduces overfitting
#   compared to a single decision tree.
# - Gives free feature importance scores -- helps explain WHY a user
#   was flagged, without needing SHAP or extra tooling.
# - No feature scaling required (tree splits don't care about scale),
#   so it's tested here without the StandardScaler step.
# =================================================================
def train_random_forest(X_train, y_train):
    """Ensemble of decision trees. Captures non-linear feature interactions."""
    model = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42)
    model.fit(X_train, y_train)
    print("[train_random_forest] Training complete")
    return model


# =================================================================
# ALGORITHM 3: XGBoost (Gradient Boosting)
# WHY THIS ALGORITHM:
# - Random Forest builds trees independently (in parallel) and averages
#   them. XGBoost builds trees SEQUENTIALLY -- each new tree is trained
#   specifically to fix the mistakes (residual errors) of the previous
#   trees. This usually produces higher accuracy than Random Forest on
#   structured/tabular data, which is exactly our data type here.
# - It's the industry-standard choice for tabular classification
#   competitions (Kaggle) and production fraud/bot-detection systems
#   for this exact reason -- strong accuracy without needing deep
#   learning.
# - Built-in regularization (via max_depth, learning_rate) helps avoid
#   overfitting despite its added complexity over Random Forest.
# =================================================================
def train_xgboost(X_train, y_train):
    """Sequentially builds trees, each correcting the previous one's errors."""
    model = XGBClassifier(
        n_estimators=200, max_depth=6, learning_rate=0.1,                    # learning_rate: how much each new tree corrects prior errors
        eval_metric="logloss", random_state=42
    )
    model.fit(X_train, y_train)
    print("[train_xgboost] Training complete")
    return model


# =================================================================
# ALGORITHM 4: LightGBM (Gradient Boosting, faster on large data)
# WHY THIS ALGORITHM:
# - Same core idea as XGBoost (sequential error-correcting trees), but
#   LightGBM grows trees LEAF-WISE instead of level-wise -- it expands
#   whichever leaf reduces error the most, rather than growing every
#   branch evenly. This makes it noticeably FASTER on large datasets
#   (we have 50,000 rows here) with usually similar or better accuracy.
# - Included alongside XGBoost specifically to COMPARE the two gradient
#   boosting variants -- in production you'd pick whichever wins on
#   your validation set and training-time budget.
# =================================================================
def train_lightgbm(X_train, y_train):
    """Similar to XGBoost but grows trees leaf-wise -- faster on large datasets."""
    model = LGBMClassifier(n_estimators=200, max_depth=6, learning_rate=0.1, random_state=42, verbosity=-1)
    model.fit(X_train, y_train)
    print("[train_lightgbm] Training complete")
    return model


# =================================================================
# ALGORITHM 5: SVM (Support Vector Machine)
# WHY THIS ALGORITHM:
# - SVM finds the best possible DIVIDING LINE (hyperplane) between the
#   bot and human classes, maximizing the margin (gap) between them --
#   a fundamentally different strategy than tree-based voting or
#   probability regression, useful to compare against.
# - LinearSVC (not kernel SVC) is used because kernel SVM does NOT
#   scale well past a few thousand rows -- it would be too slow on our
#   50,000-row dataset. LinearSVC scales fine.
# - LinearSVC has no predict_proba by default (it only outputs a raw
#   decision score, not a calibrated probability) -- so it's wrapped in
#   CalibratedClassifierCV, which fits a small extra model to convert
#   that raw score into a genuine 0-1 probability, so we can still use
#   our >0.7 / <0.3 confidence routing on its output.
# - Needs SCALED features (unlike tree models) because SVM's distance-
#   based math is sensitive to features being on different scales.
# =================================================================
def train_svm(X_train, y_train):
    """
    LinearSVC used instead of kernel SVC for speed on large datasets.
    Wrapped in CalibratedClassifierCV to get probability scores
    (LinearSVC doesn't natively output probabilities).
    """
    base_svm = LinearSVC(max_iter=2000, random_state=42)
    model = CalibratedClassifierCV(base_svm, cv=3)                          # adds probability calibration
    model.fit(X_train, y_train)
    print("[train_svm] Training complete")
    return model


# =================================================================
# ALGORITHM 6: Neural Network (MLP)
# WHY THIS ALGORITHM:
# - Included last, as the most complex option, specifically to TEST
#   whether the extra complexity of a neural network is even justified
#   for this tabular data (per the design principle: don't jump to
#   neural nets unless simpler models plateau).
# - 2 hidden layers (64 -> 32 neurons): narrowing layer sizes let the
#   network learn broad patterns first, then compress them into more
#   specific, higher-level combinations -- standard MLP design pattern.
# - ReLU activation: computationally cheap, avoids the vanishing-
#   gradient problem that older activations (sigmoid/tanh) cause in
#   hidden layers, so the network trains faster and more reliably.
# - Output layer uses a SIGMOID internally (scikit-learn handles this
#   automatically for binary classification via predict_proba) --
#   correct choice here since this is a 2-class (bot/human) problem,
#   not a 3+ class problem (which would need softmax instead).
# - early_stopping=True: stops training once validation performance
#   plateaus, preventing the network from overfitting to the training
#   set -- important since neural nets are the most overfit-prone
#   option among all 6 algorithms tested here.
# - Needs SCALED features, same reason as SVM: neural nets train far
#   more reliably when input features are on a similar numeric scale.
# =================================================================
def train_neural_network(X_train, y_train):
    """
    Multi-layer Perceptron: 2 hidden layers (64 -> 32 neurons), ReLU activation,
    sigmoid-equivalent output via predict_proba for binary classification.
    """
    model = MLPClassifier(
        hidden_layer_sizes=(64, 32),                                        # 2 hidden layers, narrowing width
        activation="relu",                                                   # ReLU: cheap, avoids vanishing gradient
        max_iter=300,
        random_state=42,
        early_stopping=True                                                  # stop if validation score plateaus
    )
    model.fit(X_train, y_train)
    print("[train_neural_network] Training complete")
    return model


# =================================================================
# STEP 7: Feature Importance (tree-based models only)
# =================================================================
def show_feature_importance(model, feature_names, top_n=10):
    """Prints top N most important features from a tree-based model."""
    importances = model.feature_importances_
    top_idx = np.argsort(importances)[::-1][:top_n]
    print(f"\n=== Top {top_n} Features ===")
    for idx in top_idx:
        print(f"{feature_names[idx]}: {importances[idx]:.4f}")


# =================================================================
# STEP 8: Confidence-Based Routing (bot / human / uncertain)
# =================================================================
def classify_with_confidence(y_prob, high_threshold=0.7, low_threshold=0.3):
    """Routes each prediction into bot / human / uncertain based on probability."""
    decisions = []
    for p in y_prob:
        if p >= high_threshold:
            decisions.append("bot")
        elif p <= low_threshold:
            decisions.append("human")
        else:
            decisions.append("uncertain")
    print(f"\n=== Confidence Routing ===")
    print(f"Bot: {decisions.count('bot')}, Human: {decisions.count('human')}, "
          f"Uncertain: {decisions.count('uncertain')}")
    return decisions


# =================================================================
# MAIN: Run the full pipeline step by step
# =================================================================
def main():
    # Step 1-2: Load and engineer features
    df = load_data()
    df = engineer_features(df)

    # Step 3: Build feature matrix
    X, y, tfidf, feature_names = build_feature_matrix(df)

    # Step 4: Split
    X_train, X_test, y_train, y_test = split_data(X, y)

    # Step 5: Scale (needed for LR, SVM, MLP -- tree models don't need it)
    X_train_scaled, X_test_scaled, scaler = scale_features(X_train, X_test)

    # ---- Algorithm 1: Logistic Regression ----
    log_model = train_logistic_regression(X_train_scaled, y_train)
    evaluate_model("Logistic Regression", log_model, X_test_scaled, y_test)

    # ---- Algorithm 2: Random Forest (no scaling needed) ----
    rf_model = train_random_forest(X_train, y_train)
    evaluate_model("Random Forest", rf_model, X_test, y_test)
    show_feature_importance(rf_model, feature_names)

    # ---- Algorithm 3: XGBoost (no scaling needed) ----
    xgb_model = train_xgboost(X_train, y_train)
    evaluate_model("XGBoost", xgb_model, X_test, y_test)
    show_feature_importance(xgb_model, feature_names)

    # ---- Algorithm 4: LightGBM (no scaling needed) ----
    lgbm_model = train_lightgbm(X_train, y_train)
    evaluate_model("LightGBM", lgbm_model, X_test, y_test)
    show_feature_importance(lgbm_model, feature_names)

    # ---- Algorithm 5: SVM (needs scaling) ----
    svm_model = train_svm(X_train_scaled, y_train)
    _, svm_scores = evaluate_model("SVM", svm_model, X_test_scaled, y_test)

    # ---- Algorithm 6: Neural Network / MLP (needs scaling) ----
    mlp_model = train_neural_network(X_train_scaled, y_train)
    _, mlp_probs = evaluate_model("Neural Network (MLP)", mlp_model, X_test_scaled, y_test)

    # ---- Step 8: Confidence routing example using MLP probabilities ----
    classify_with_confidence(mlp_probs)


if __name__ == "__main__":
    main()
