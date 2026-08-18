"""
Twitter Bot Detector — using bot_detection_data.csv
Step-by-step: load -> feature engineer -> train -> evaluate -> predict
"""

import pandas as pd                                          # data loading & manipulation
import numpy as np                                            # numerical operations
from sklearn.model_selection import train_test_split          # train/test split
from sklearn.linear_model import LogisticRegression            # baseline model
from sklearn.ensemble import RandomForestClassifier             # stronger tree-based model
from sklearn.preprocessing import StandardScaler                # feature scaling
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score  # evaluation
from sklearn.feature_extraction.text import TfidfVectorizer      # convert tweet text to numeric features

# ---------------------------------------------------------------
# STEP 1: Load the dataset
# ---------------------------------------------------------------
df = pd.read_csv("/mnt/user-data/uploads/bot_detection_data.csv")

print("=== Dataset Overview ===")
print(f"Shape: {df.shape}")                                    # (rows, columns)
print(f"Bot label distribution:\n{df['Bot Label'].value_counts()}")  # check class balance

# ---------------------------------------------------------------
# STEP 2: Feature Engineering
# Why: raw columns like Username/Location/Created At aren't directly
# usable by a model -- we convert them into numeric signals.
# ---------------------------------------------------------------

# 2a) Convert boolean Verified column to 0/1 integer
df["Verified"] = df["Verified"].astype(int)

# 2b) Hashtag count -- bots often either spam many hashtags or use none
# Fill missing hashtags with empty string, then count words
df["Hashtags"] = df["Hashtags"].fillna("")
df["Hashtag_Count"] = df["Hashtags"].apply(lambda x: len(x.split()) if x else 0)

# 2c) Tweet length -- bots often generate oddly short/long templated text
df["Tweet_Length"] = df["Tweet"].apply(len)

# 2d) Extract hour of day from Created At -- bots often post at unnatural hours (e.g. 3 AM bursts)
df["Created At"] = pd.to_datetime(df["Created At"])
df["Post_Hour"] = df["Created At"].dt.hour

# 2e) Engagement ratio -- retweets relative to follower count
# Why: a bot with few followers getting oddly high retweets is suspicious
# add 1 to avoid division by zero
df["Retweet_Per_Follower"] = df["Retweet Count"] / (df["Follower Count"] + 1)

# ---------------------------------------------------------------
# STEP 3: Select numeric features for the model
# ---------------------------------------------------------------
numeric_features = [
    "Retweet Count",
    "Mention Count",
    "Follower Count",
    "Verified",
    "Hashtag_Count",
    "Tweet_Length",
    "Post_Hour",
    "Retweet_Per_Follower",
]

X_numeric = df[numeric_features].values                        # feature matrix
y = df["Bot Label"].values                                       # target labels (0/1)

# ---------------------------------------------------------------
# STEP 4: Convert Tweet text into numeric features using TF-IDF
# Why: Tweet content itself may carry signal (repetitive/templated
# language is common in bot-generated tweets)
# ---------------------------------------------------------------
tfidf = TfidfVectorizer(max_features=100, stop_words="english")  # limit to top 100 words, keeps it fast
X_text = tfidf.fit_transform(df["Tweet"]).toarray()               # convert tweets to numeric vectors

# ---------------------------------------------------------------
# STEP 5: Combine numeric + text features into one matrix
# ---------------------------------------------------------------
X = np.hstack([X_numeric, X_text])                               # side-by-side concatenation

# ---------------------------------------------------------------
# STEP 6: Train/test split
# ---------------------------------------------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y             # stratify keeps 50/50 class balance in both sets
)

# ---------------------------------------------------------------
# STEP 7: Scale numeric features
# Why: Logistic Regression is sensitive to feature scale
# (Follower Count in thousands vs Verified as 0/1 would dominate otherwise)
# ---------------------------------------------------------------
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)                   # fit scaler on train data only
X_test_scaled = scaler.transform(X_test)                          # apply same scaling to test data

# ---------------------------------------------------------------
# STEP 8: Train baseline model -- Logistic Regression
# ---------------------------------------------------------------
print("\n=== Training Logistic Regression (baseline) ===")
log_model = LogisticRegression(max_iter=1000)
log_model.fit(X_train_scaled, y_train)

y_pred_log = log_model.predict(X_test_scaled)
y_prob_log = log_model.predict_proba(X_test_scaled)[:, 1]         # probability of being a bot

print(classification_report(y_test, y_pred_log, target_names=["human", "bot"]))
print(f"ROC-AUC: {roc_auc_score(y_test, y_prob_log):.3f}")

# ---------------------------------------------------------------
# STEP 9: Train stronger model -- Random Forest
# Why: captures non-linear feature interactions Logistic Regression misses
# (e.g. "high retweets is normal ONLY IF verified" -- an interaction effect)
# ---------------------------------------------------------------
print("\n=== Training Random Forest ===")
rf_model = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42)
rf_model.fit(X_train, y_train)                                     # tree models don't need scaling

y_pred_rf = rf_model.predict(X_test)
y_prob_rf = rf_model.predict_proba(X_test)[:, 1]

print(classification_report(y_test, y_pred_rf, target_names=["human", "bot"]))
print(f"ROC-AUC: {roc_auc_score(y_test, y_prob_rf):.3f}")

# ---------------------------------------------------------------
# STEP 10: Feature importance -- which signals matter most
# Why: helps you explain decisions (interpretability) and refine features
# ---------------------------------------------------------------
feature_names = numeric_features + [f"tfidf_{w}" for w in tfidf.get_feature_names_out()]
importances = rf_model.feature_importances_

top_10_idx = np.argsort(importances)[::-1][:10]                    # top 10 most important features
print("\n=== Top 10 Most Important Features (Random Forest) ===")
for idx in top_10_idx:
    print(f"{feature_names[idx]}: {importances[idx]:.4f}")

# ---------------------------------------------------------------
# STEP 11: Confidence-based routing (matches your earlier design)
# >0.7 = bot, <0.3 = human, in between = uncertain -> needs review
# ---------------------------------------------------------------
def classify_user(prob_bot, high_threshold=0.7, low_threshold=0.3):
    """Route prediction based on confidence, same pattern as prior chatbot design."""
    if prob_bot >= high_threshold:
        return "bot"
    elif prob_bot <= low_threshold:
        return "human"
    else:
        return "uncertain"                                          # needs human review / feedback loop

# Apply routing to test set predictions
decisions = [classify_user(p) for p in y_prob_rf]
uncertain_count = decisions.count("uncertain")
print(f"\n=== Confidence Routing on Test Set ===")
print(f"Bot (confident): {decisions.count('bot')}")
print(f"Human (confident): {decisions.count('human')}")
print(f"Uncertain (needs review): {uncertain_count} ({uncertain_count/len(decisions)*100:.1f}%)")