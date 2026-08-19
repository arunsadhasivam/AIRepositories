# Master Algorithm Reference: EDA, ML, Deep Learning, Computer Vision

Each row: S.No | Algorithm | Description | YouTube (search link). Numbering resets per section.


---

## Learning Order: Why Each Stage Comes Before the Next

| Stage | Category | Why It Comes at This Point |
|---|---|---|
| 1 | Exploratory Data Analysis (EDA) | Can't build any model without knowing data shape, missing values, outliers first |
| 2 | Feature Engineering / Preprocessing | Raw data from EDA isn't model-ready — needs encoding/scaling before any algorithm can use it |
| 3 | Ensemble / Classical ML | Simplest models that actually learn patterns; foundation before adding complexity |
| 4 | Model Evaluation Metrics | Need a way to judge if a model is actually good, not just built |
| 5 | Generalization / Avoiding Overfitting | A model can look good on training data and fail in reality — must catch this before trusting bigger models |
| 6 | Hyperparameter Tuning | Optimize a model only after you can validate it's trustworthy |
| 7 | Bayesian Methods | Probabilistic reasoning rounds out classical ML — still shallow/interpretable, near the ceiling of classical ML |
| 8 | Association Rule Mining | Pattern-mining is the last classical/interpretable technique — its limits on images/text/sequences are exactly why Deep Learning is needed next |
| 9 | Deep Learning (Perceptron → MLP → CNN → RNN/LSTM → Transformer → RL) | Classical ML can't auto-learn features from raw pixels/text/audio; DL learns features directly, but needs steps 1-8 to avoid massive overfitting |
| 10 | Computer Vision | Specialized DL architectures built on CNNs from step 9 (detection, segmentation, GANs) |
| 11 | NLP-specific | Transformers from step 9 applied specifically to text |
| 12 | Time Series | LSTM-based forecasting depends on RNN/LSTM fundamentals from step 9 |
| 13 | Recommendation Systems | Neural Collaborative Filtering needs neural network fundamentals from step 9 |
| 14 | Explainability (XAI) | Can only explain a model once it's complex enough to need explaining (e.g. Grad-CAM needs a trained CNN from step 10) |
| 15 | Transfer Learning / Fine-Tuning | Requires a pretrained deep model (steps 9-11) to already exist before reusing/adapting it |
| 16 | Self-Supervised / Contrastive Learning | Advanced pretraining strategy; needs supervised DL understood first to see why label-free learning differs |
| 17 | AutoML | Automates everything above — only makes sense once you understand what's being automated |

---


<details>
<summary><h2>1. Exploratory Data Analysis (EDA)</h2></summary>

**Why here:** You can't build any model without knowing your data — shape, missing values, outliers, correlations. Skipping this means building models on garbage data.

**Unlocks:** You now understand what the data actually looks like.

**Reference:**
- Book: "Python for Data Analysis" by Wes McKinney
- Site: https://www.kaggle.com/learn/data-cleaning
- Site: https://seaborn.pydata.org/tutorial.html

| S.No | Algorithm | Description | YouTube |
|---|---|---|---|
| 1 | Histogram | Visualize the distribution shape of a single variable | [Watch](https://www.youtube.com/results?search_query=Histogram%20explained) |
| 2 | Box Plot | Show median, quartiles, and outliers at a glance | [Watch](https://www.youtube.com/results?search_query=Box%20Plot%20explained) |
| 3 | Violin Plot | Combine box plot with distribution density | [Watch](https://www.youtube.com/results?search_query=Violin%20Plot%20explained) |
| 4 | Q-Q Plot | Check whether data follows a normal distribution | [Watch](https://www.youtube.com/results?search_query=Q-Q%20Plot%20explained) |
| 5 | Skewness & Kurtosis | Measure asymmetry and tail-heaviness of a distribution | [Watch](https://www.youtube.com/results?search_query=Skewness%20%26%20Kurtosis%20explained) |
| 6 | Correlation Analysis (Pearson/Spearman/Kendall) | Measure strength/direction of relationship between two variables | [Watch](https://www.youtube.com/results?search_query=Correlation%20Analysis%20%28Pearson/Spearman/Kendall%29%20explained) |
| 7 | Scatter Plot / Pair Plot | Visualize relationships between variable pairs | [Watch](https://www.youtube.com/results?search_query=Scatter%20Plot%20/%20Pair%20Plot%20explained) |
| 8 | Cross-tabulation / Chi-Square Test | Test relationship between two categorical variables | [Watch](https://www.youtube.com/results?search_query=Cross-tabulation%20/%20Chi-Square%20Test%20explained) |
| 9 | Covariance Matrix | Measure how variables vary together | [Watch](https://www.youtube.com/results?search_query=Covariance%20Matrix%20explained) |
| 10 | Heatmap | Visualize a correlation/matrix using color intensity | [Watch](https://www.youtube.com/results?search_query=Heatmap%20explained) |
| 11 | PCA | Reduce dimensions while keeping maximum variance | [Watch](https://www.youtube.com/results?search_query=PCA%20explained) |
| 12 | t-SNE | Visualize high-dimensional data in 2D/3D preserving local structure | [Watch](https://www.youtube.com/results?search_query=t-SNE%20explained) |
| 13 | UMAP | Faster nonlinear dimensionality reduction preserving local + global structure | [Watch](https://www.youtube.com/results?search_query=UMAP%20explained) |
| 14 | LDA (dimensionality) | Reduce dimensions while maximizing class separability | [Watch](https://www.youtube.com/results?search_query=LDA%20%28dimensionality%29%20explained) |
| 15 | Factor Analysis | Find hidden (latent) variables explaining correlations | [Watch](https://www.youtube.com/results?search_query=Factor%20Analysis%20explained) |
| 16 | SVD | Decompose a matrix for compression/dimensionality reduction | [Watch](https://www.youtube.com/results?search_query=SVD%20explained) |
| 17 | Z-Score Method | Flag outliers based on standard deviations from mean | [Watch](https://www.youtube.com/results?search_query=Z-Score%20Method%20explained) |
| 18 | IQR Method | Flag outliers using the interquartile range | [Watch](https://www.youtube.com/results?search_query=IQR%20Method%20explained) |
| 19 | Isolation Forest | Detect anomalies by how easily a point gets isolated | [Watch](https://www.youtube.com/results?search_query=Isolation%20Forest%20explained) |
| 20 | Local Outlier Factor (LOF) | Detect outliers via local density deviation | [Watch](https://www.youtube.com/results?search_query=Local%20Outlier%20Factor%20%28LOF%29%20explained) |
| 21 | DBSCAN (outlier use) | Flag points that don't belong to any dense region | [Watch](https://www.youtube.com/results?search_query=DBSCAN%20%28outlier%20use%29%20explained) |
| 22 | Missing Pattern Visualization | Spot patterns in where data is missing | [Watch](https://www.youtube.com/results?search_query=Missing%20Pattern%20Visualization%20explained) |
| 23 | Mean/Median/Mode Imputation | Fill missing values with central tendency | [Watch](https://www.youtube.com/results?search_query=Mean/Median/Mode%20Imputation%20explained) |
| 24 | KNN Imputer | Fill missing values using nearest neighbors' values | [Watch](https://www.youtube.com/results?search_query=KNN%20Imputer%20explained) |
| 25 | MICE | Iteratively impute missing values using regression chains | [Watch](https://www.youtube.com/results?search_query=MICE%20explained) |
| 26 | K-Means | Partition data into K groups by similarity | [Watch](https://www.youtube.com/results?search_query=K-Means%20explained) |
| 27 | Hierarchical Clustering | Build nested clusters shown as a dendrogram | [Watch](https://www.youtube.com/results?search_query=Hierarchical%20Clustering%20explained) |
| 28 | DBSCAN (clustering use) | Cluster by density, handles irregular shapes | [Watch](https://www.youtube.com/results?search_query=DBSCAN%20%28clustering%20use%29%20explained) |
| 29 | Gaussian Mixture Model (GMM) | Soft/probabilistic clustering | [Watch](https://www.youtube.com/results?search_query=Gaussian%20Mixture%20Model%20%28GMM%29%20explained) |
| 30 | Spectral Clustering | Cluster using graph connectivity/eigenvalues, handles non-convex shapes | [Watch](https://www.youtube.com/results?search_query=Spectral%20Clustering%20explained) |
| 31 | Mean Shift Clustering | Cluster by shifting points toward areas of higher density | [Watch](https://www.youtube.com/results?search_query=Mean%20Shift%20Clustering%20explained) |
| 32 | Affinity Propagation | Cluster by passing messages between points to find exemplars, no need to preset cluster count | [Watch](https://www.youtube.com/results?search_query=Affinity%20Propagation%20explained) |
| 33 | OPTICS | Density-based clustering that handles varying density better than DBSCAN | [Watch](https://www.youtube.com/results?search_query=OPTICS%20explained) |
| 34 | Self-Organizing Maps (SOM) | Neural network that maps high-dimensional data onto a low-dimensional grid, preserving topology | [Watch](https://www.youtube.com/results?search_query=Self-Organizing%20Maps%20%28SOM%29%20explained) |
| 35 | Feature Importance (tree-based) | Rank features by predictive contribution | [Watch](https://www.youtube.com/results?search_query=Feature%20Importance%20%28tree-based%29%20explained) |
| 36 | Mutual Information | Measure dependency between a feature and the target | [Watch](https://www.youtube.com/results?search_query=Mutual%20Information%20explained) |
| 37 | Variance Threshold | Drop low-variance, uninformative features | [Watch](https://www.youtube.com/results?search_query=Variance%20Threshold%20explained) |
| 38 | ANOVA F-test | Test if a feature's mean differs significantly across groups | [Watch](https://www.youtube.com/results?search_query=ANOVA%20F-test%20explained) |

</details>


<details>
<summary><h2>2. Feature Engineering / Preprocessing</h2></summary>

**Why here:** Raw data from EDA still isn't model-ready — categories need encoding, scales need normalizing. Models fail or perform poorly without this.

**Unlocks:** Clean, numeric, scaled input any algorithm can consume.

**Reference:**
- Book: "Feature Engineering for Machine Learning" by Alice Zheng & Amanda Casari
- Site: https://scikit-learn.org/stable/modules/preprocessing.html
- Site: https://www.kaggle.com/learn/feature-engineering

| S.No | Algorithm | Description | YouTube |
|---|---|---|---|
| 1 | StandardScaler (Z-score scaling) | Rescale features to mean 0, std 1 so no feature dominates due to scale | [Watch](https://www.youtube.com/results?search_query=StandardScaler%20%28Z-score%20scaling%29%20explained) |
| 2 | MinMax Scaling | Rescale features to a fixed range, typically 0 to 1 | [Watch](https://www.youtube.com/results?search_query=MinMax%20Scaling%20explained) |
| 3 | Robust Scaling | Scale using median/IQR, resistant to outliers | [Watch](https://www.youtube.com/results?search_query=Robust%20Scaling%20explained) |
| 4 | One-Hot Encoding | Convert categorical values into binary columns for ML models | [Watch](https://www.youtube.com/results?search_query=One-Hot%20Encoding%20explained) |
| 5 | Label Encoding | Convert categories into integer codes | [Watch](https://www.youtube.com/results?search_query=Label%20Encoding%20explained) |
| 6 | Target Encoding | Encode categories using the mean of the target variable | [Watch](https://www.youtube.com/results?search_query=Target%20Encoding%20explained) |
| 7 | Binning/Discretization | Convert continuous values into discrete buckets | [Watch](https://www.youtube.com/results?search_query=Binning/Discretization%20explained) |
| 8 | Log/Box-Cox Transform | Transform skewed data to be closer to normal distribution | [Watch](https://www.youtube.com/results?search_query=Log/Box-Cox%20Transform%20explained) |
| 9 | Polynomial Features | Generate interaction/higher-order terms to capture non-linearity | [Watch](https://www.youtube.com/results?search_query=Polynomial%20Features%20explained) |

</details>


<details>
<summary><h2>3. Ensemble / Classical ML</h2></summary>

**Why here:** These are the simplest models that actually learn patterns. You must understand a single Decision Tree before understanding why Random Forest (many trees) or Boosting (sequential correction) improves it.

**Unlocks:** A working baseline model and the core idea of "learning from data" before adding neural complexity.

**Reference:**
- Book: "The Elements of Statistical Learning" by Hastie, Tibshirani, Friedman
- Book: "Hands-On Machine Learning" by Aurelien Geron
- Site: https://scikit-learn.org/stable/user_guide.html

| S.No | Algorithm | Description | YouTube |
|---|---|---|---|
| 1 | Decision Tree | Split data on feature thresholds to predict a label/value | [Watch](https://www.youtube.com/results?search_query=Decision%20Tree%20explained) |
| 2 | Linear Regression | Predict a continuous value from a linear combination of features | [Watch](https://www.youtube.com/results?search_query=Linear%20Regression%20explained) |
| 3 | Logistic Regression | Predict a class probability using a linear decision boundary | [Watch](https://www.youtube.com/results?search_query=Logistic%20Regression%20explained) |
| 4 | K-Nearest Neighbors (KNN) | Classify/predict based on the closest training examples | [Watch](https://www.youtube.com/results?search_query=K-Nearest%20Neighbors%20%28KNN%29%20explained) |
| 5 | Support Vector Machine (SVM) | Find the maximum-margin boundary between classes | [Watch](https://www.youtube.com/results?search_query=Support%20Vector%20Machine%20%28SVM%29%20explained) |
| 6 | Naive Bayes | Classify using Bayes' theorem assuming feature independence | [Watch](https://www.youtube.com/results?search_query=Naive%20Bayes%20explained) |
| 7 | Polynomial Regression | Fit a curved (non-linear) relationship by adding polynomial terms to linear regression | [Watch](https://www.youtube.com/results?search_query=Polynomial%20Regression%20explained) |
| 8 | Quadratic Discriminant Analysis (QDA) | Classify assuming each class has its own Gaussian distribution with different covariance | [Watch](https://www.youtube.com/results?search_query=Quadratic%20Discriminant%20Analysis%20%28QDA%29%20explained) |
| 9 | Linear Discriminant Analysis (classifier use) | Classify by projecting data onto a line that best separates classes | [Watch](https://www.youtube.com/results?search_query=Linear%20Discriminant%20Analysis%20%28classifier%20use%29%20explained) |
| 10 | Random Forest | Average many decision trees (bagging) to reduce variance | [Watch](https://www.youtube.com/results?search_query=Random%20Forest%20explained) |
| 11 | Bagging | Train models on random data subsets and average results | [Watch](https://www.youtube.com/results?search_query=Bagging%20explained) |
| 12 | Extra Trees | Like Random Forest but extra randomness in splits, faster | [Watch](https://www.youtube.com/results?search_query=Extra%20Trees%20explained) |
| 13 | AdaBoost | Sequentially boost weak learners by reweighting misclassified points | [Watch](https://www.youtube.com/results?search_query=AdaBoost%20explained) |
| 14 | Gradient Boosting (GBM) | Sequentially fit models to the residual errors | [Watch](https://www.youtube.com/results?search_query=Gradient%20Boosting%20%28GBM%29%20explained) |
| 15 | XGBoost | Regularized, optimized gradient boosting for speed and accuracy | [Watch](https://www.youtube.com/results?search_query=XGBoost%20explained) |
| 16 | LightGBM | Leaf-wise gradient boosting, very fast on large datasets | [Watch](https://www.youtube.com/results?search_query=LightGBM%20explained) |
| 17 | CatBoost | Gradient boosting optimized for categorical features | [Watch](https://www.youtube.com/results?search_query=CatBoost%20explained) |
| 18 | Stacking | Combine multiple models' predictions using a meta-model | [Watch](https://www.youtube.com/results?search_query=Stacking%20explained) |
| 19 | Blending | Like stacking but meta-model trained on a held-out validation set | [Watch](https://www.youtube.com/results?search_query=Blending%20explained) |

</details>


<details>
<summary><h2>4. Model Evaluation Metrics</h2></summary>

**Why here:** Once you have a model, you need to know if it's actually good. Without this, you can't tell a good model from a lucky/bad one.

**Unlocks:** A way to judge every model you build from here on.

**Reference:**
- Book: "Evaluating Machine Learning Models" by Alice Zheng
- Site: https://scikit-learn.org/stable/modules/model_evaluation.html
- Site: https://developers.google.com/machine-learning/crash-course/classification/metrics

| S.No | Algorithm | Description | YouTube |
|---|---|---|---|
| 1 | Accuracy | Fraction of correct predictions out of total predictions | [Watch](https://www.youtube.com/results?search_query=Accuracy%20explained) |
| 2 | Precision | Of predicted positives, how many were actually positive | [Watch](https://www.youtube.com/results?search_query=Precision%20explained) |
| 3 | Recall (Sensitivity) | Of actual positives, how many were correctly predicted | [Watch](https://www.youtube.com/results?search_query=Recall%20%28Sensitivity%29%20explained) |
| 4 | F1 Score | Harmonic mean of precision and recall | [Watch](https://www.youtube.com/results?search_query=F1%20Score%20explained) |
| 5 | ROC-AUC | Measures ability to distinguish classes across all thresholds | [Watch](https://www.youtube.com/results?search_query=ROC-AUC%20explained) |
| 6 | Confusion Matrix | Table showing true/false positives and negatives | [Watch](https://www.youtube.com/results?search_query=Confusion%20Matrix%20explained) |
| 7 | RMSE (Root Mean Squared Error) | Measures average prediction error magnitude, penalizes large errors | [Watch](https://www.youtube.com/results?search_query=RMSE%20%28Root%20Mean%20Squared%20Error%29%20explained) |
| 8 | MAE (Mean Absolute Error) | Measures average absolute prediction error | [Watch](https://www.youtube.com/results?search_query=MAE%20%28Mean%20Absolute%20Error%29%20explained) |
| 9 | R² Score | Measures how much variance in target is explained by the model | [Watch](https://www.youtube.com/results?search_query=R%C2%B2%20Score%20explained) |
| 10 | Log Loss | Penalizes confident wrong probability predictions in classification | [Watch](https://www.youtube.com/results?search_query=Log%20Loss%20explained) |

</details>


<details>
<summary><h2>5. Generalization / Avoiding Overfitting</h2></summary>

**Why here:** A model can score well on training data and still fail in the real world. This stage teaches you to detect and prevent that trap — critical before models get more complex (deep learning overfits far more easily).

**Unlocks:** The discipline needed before trusting any larger model.

**Reference:**
- Book: "Deep Learning" by Goodfellow, Bengio, Courville — Chapter 5 & 7
- Site: https://www.deeplearningbook.org/
- Site: https://developers.google.com/machine-learning/crash-course/overfitting

| S.No | Algorithm | Description | YouTube |
|---|---|---|---|
| 1 | Train/Validation/Test Split | Hold out data to measure real-world performance | [Watch](https://www.youtube.com/results?search_query=Train/Validation/Test%20Split%20explained) |
| 2 | Cross-Validation (K-Fold, Stratified, LOO) | Validate robustly across multiple splits | [Watch](https://www.youtube.com/results?search_query=Cross-Validation%20%28K-Fold%2C%20Stratified%2C%20LOO%29%20explained) |
| 3 | Data Augmentation | Synthetically expand training data variety | [Watch](https://www.youtube.com/results?search_query=Data%20Augmentation%20explained) |
| 4 | SMOTE / Under/Oversampling | Rebalance classes to avoid biased learning | [Watch](https://www.youtube.com/results?search_query=SMOTE%20/%20Under/Oversampling%20explained) |
| 5 | L1 Regularization (Lasso) | Shrink and zero-out less useful feature weights | [Watch](https://www.youtube.com/results?search_query=L1%20Regularization%20%28Lasso%29%20explained) |
| 6 | L2 Regularization (Ridge) | Shrink weights smoothly to reduce overfitting | [Watch](https://www.youtube.com/results?search_query=L2%20Regularization%20%28Ridge%29%20explained) |
| 7 | ElasticNet | Combine L1 + L2 regularization | [Watch](https://www.youtube.com/results?search_query=ElasticNet%20explained) |
| 8 | Pruning (Decision Trees) | Cut back tree branches to reduce overfitting | [Watch](https://www.youtube.com/results?search_query=Pruning%20%28Decision%20Trees%29%20explained) |
| 9 | Max Depth / Min Samples Leaf | Constrain tree size to limit memorization | [Watch](https://www.youtube.com/results?search_query=Max%20Depth%20/%20Min%20Samples%20Leaf%20explained) |
| 10 | Dropout (generalization use) | Randomly drop neurons to prevent co-adaptation | [Watch](https://www.youtube.com/results?search_query=Dropout%20%28generalization%20use%29%20explained) |
| 11 | Batch Normalization (generalization use) | Stabilizes training, mild regularizing effect | [Watch](https://www.youtube.com/results?search_query=Batch%20Normalization%20%28generalization%20use%29%20explained) |
| 12 | Early Stopping | Stop training when validation performance stops improving | [Watch](https://www.youtube.com/results?search_query=Early%20Stopping%20explained) |
| 13 | Weight Decay | Penalize large weights during optimization | [Watch](https://www.youtube.com/results?search_query=Weight%20Decay%20explained) |
| 14 | Label Smoothing | Soften target labels to reduce overconfidence | [Watch](https://www.youtube.com/results?search_query=Label%20Smoothing%20explained) |
| 15 | Gradient Clipping | Cap gradients to prevent unstable training | [Watch](https://www.youtube.com/results?search_query=Gradient%20Clipping%20explained) |
| 16 | Noise Injection | Add noise to inputs/weights to improve robustness | [Watch](https://www.youtube.com/results?search_query=Noise%20Injection%20explained) |
| 17 | Bagging (generalization use) | Reduce variance by averaging diverse models | [Watch](https://www.youtube.com/results?search_query=Bagging%20%28generalization%20use%29%20explained) |
| 18 | Boosting (generalization caution) | Reduces bias but needs early stopping to avoid overfitting | [Watch](https://www.youtube.com/results?search_query=Boosting%20%28generalization%20caution%29%20explained) |
| 19 | Learning Curves | Plot train vs. validation loss to diagnose over/underfitting | [Watch](https://www.youtube.com/results?search_query=Learning%20Curves%20explained) |
| 20 | Bias-Variance Tradeoff Analysis | Balance underfitting vs. overfitting | [Watch](https://www.youtube.com/results?search_query=Bias-Variance%20Tradeoff%20Analysis%20explained) |

</details>


<details>
<summary><h2>6. Hyperparameter Tuning</h2></summary>

**Why here:** Now that you can build and validate a model, you optimize it. Doing this before generalization would mean tuning a model you don't even know is trustworthy.

**Unlocks:** A properly optimized classical model — the ceiling of "shallow" ML.

**Reference:**
- Site: https://scikit-learn.org/stable/modules/grid_search.html
- Site: https://optuna.org/
- Site: https://www.jeremyjordan.me/hyperparameter-tuning/

| S.No | Algorithm | Description | YouTube |
|---|---|---|---|
| 1 | Grid Search | Exhaustively try every combination of parameters in a defined grid | [Watch](https://www.youtube.com/results?search_query=Grid%20Search%20explained) |
| 2 | Random Search | Randomly sample parameter combinations, often faster than grid search | [Watch](https://www.youtube.com/results?search_query=Random%20Search%20explained) |
| 3 | Bayesian Optimization (Optuna, Hyperopt) | Use past trial results to intelligently pick the next parameters to try | [Watch](https://www.youtube.com/results?search_query=Bayesian%20Optimization%20%28Optuna%2C%20Hyperopt%29%20explained) |
| 4 | Hyperband / Successive Halving | Allocate more resources to promising configurations early | [Watch](https://www.youtube.com/results?search_query=Hyperband%20/%20Successive%20Halving%20explained) |

</details>


<details>
<summary><h2>7. Bayesian Methods</h2></summary>

**Why here:** These round out classical ML with probabilistic reasoning — still shallow/interpretable models, the last stop before neural networks.

**Unlocks:** Full classical ML toolkit. At this point classical models plateau on complex data — this limitation is why you need Deep Learning next.

**Reference:**
- Book: "Pattern Recognition and Machine Learning" by Christopher Bishop
- Book: "Bayesian Reasoning and Machine Learning" by David Barber
- Site: https://www.cs.ubc.ca/~murphyk/MLbook/

| S.No | Algorithm | Description | YouTube |
|---|---|---|---|
| 1 | Bayesian Networks | Model probabilistic dependencies between variables using a directed graph | [Watch](https://www.youtube.com/results?search_query=Bayesian%20Networks%20explained) |
| 2 | Gaussian Processes | Model a distribution over functions for probabilistic regression | [Watch](https://www.youtube.com/results?search_query=Gaussian%20Processes%20explained) |
| 3 | Naive Bayes (Bayesian use) | Classify using Bayes' theorem with a simplifying independence assumption | [Watch](https://www.youtube.com/results?search_query=Naive%20Bayes%20%28Bayesian%20use%29%20explained) |
| 4 | Markov Chain Monte Carlo (MCMC) | Sample from complex probability distributions to estimate posteriors | [Watch](https://www.youtube.com/results?search_query=Markov%20Chain%20Monte%20Carlo%20%28MCMC%29%20explained) |
| 5 | Bayesian Linear Regression | Regression that outputs a distribution over predictions, not just a point estimate | [Watch](https://www.youtube.com/results?search_query=Bayesian%20Linear%20Regression%20explained) |

</details>


<details>
<summary><h2>8. Association Rule Mining</h2></summary>

**Why here:** Pattern-mining rounds out classical ML — still a shallow, interpretable technique, one of the last stops before neural networks.

**Unlocks:** Full classical ML toolkit. This limitation on complex data (images, text, sequences) is exactly why Deep Learning is needed next.

**Reference:**
- Book: "Data Mining: Concepts and Techniques" by Han, Kamber, Pei
- Site: https://www.kaggle.com/learn/intro-to-data-mining (search: market basket analysis)

| S.No | Algorithm | Description | YouTube |
|---|---|---|---|
| 1 | Apriori | Find frequent itemsets and generate association rules (e.g., market basket analysis) | [Watch](https://www.youtube.com/results?search_query=Apriori%20explained) |
| 2 | FP-Growth | Faster frequent itemset mining without candidate generation, using a tree structure | [Watch](https://www.youtube.com/results?search_query=FP-Growth%20explained) |
| 3 | Eclat | Mine frequent itemsets using a vertical data format and set intersections | [Watch](https://www.youtube.com/results?search_query=Eclat%20explained) |

</details>


<details>
<summary><h2>9. Deep Learning</h2></summary>

**Why here:** Classical ML can't automatically learn features from raw pixels, audio, or long text sequences — you'd have to hand-engineer them. Deep Learning solves this by learning features directly from raw data, but it needs everything before it (clean data, evaluation, regularization) to avoid massively overfitting on its huge parameter count.

**Unlocks:** The ability to learn features directly from raw, unstructured data.

**Reference:**
- Book: "Deep Learning" by Goodfellow, Bengio, Courville
- Site: https://www.deeplearningbook.org/
- Site: https://cs231n.stanford.edu/ (Stanford CS231n)
- Site: https://d2l.ai/ (Dive into Deep Learning)

| S.No | Algorithm | Description | YouTube |
|---|---|---|---|
| 1 | Perceptron | The single-neuron building block of neural networks | [Watch](https://www.youtube.com/results?search_query=Perceptron%20explained) |
| 2 | Multi-Layer Perceptron (MLP) | Stack of fully connected layers for general prediction | [Watch](https://www.youtube.com/results?search_query=Multi-Layer%20Perceptron%20%28MLP%29%20explained) |
| 3 | LeNet | Early CNN for simple digit/image recognition | [Watch](https://www.youtube.com/results?search_query=LeNet%20explained) |
| 4 | AlexNet | Deeper CNN that popularized deep learning for image classification | [Watch](https://www.youtube.com/results?search_query=AlexNet%20explained) |
| 5 | VGG | Very deep CNN using small stacked filters | [Watch](https://www.youtube.com/results?search_query=VGG%20explained) |
| 6 | GoogLeNet (Inception) | CNN using parallel multi-scale filters for efficiency | [Watch](https://www.youtube.com/results?search_query=GoogLeNet%20%28Inception%29%20explained) |
| 7 | ResNet | CNN with skip connections to train very deep networks | [Watch](https://www.youtube.com/results?search_query=ResNet%20explained) |
| 8 | DenseNet | CNN where each layer connects to all previous layers | [Watch](https://www.youtube.com/results?search_query=DenseNet%20explained) |
| 9 | EfficientNet | CNN scaled systematically for accuracy vs. compute tradeoff | [Watch](https://www.youtube.com/results?search_query=EfficientNet%20explained) |
| 10 | MobileNet | Lightweight CNN designed for mobile/edge devices | [Watch](https://www.youtube.com/results?search_query=MobileNet%20explained) |
| 11 | Xception | CNN using depthwise separable convolutions for efficiency | [Watch](https://www.youtube.com/results?search_query=Xception%20explained) |
| 12 | RNN | Processes sequences by passing a hidden state forward in time | [Watch](https://www.youtube.com/results?search_query=RNN%20explained) |
| 13 | LSTM | RNN variant that handles long-term dependencies via gates | [Watch](https://www.youtube.com/results?search_query=LSTM%20explained) |
| 14 | GRU | Simplified LSTM with fewer gates, faster to train | [Watch](https://www.youtube.com/results?search_query=GRU%20explained) |
| 15 | Bidirectional RNN/LSTM | Reads sequence both forward and backward for context | [Watch](https://www.youtube.com/results?search_query=Bidirectional%20RNN/LSTM%20explained) |
| 16 | Seq2Seq (Encoder-Decoder) | Maps an input sequence to an output sequence | [Watch](https://www.youtube.com/results?search_query=Seq2Seq%20%28Encoder-Decoder%29%20explained) |
| 17 | Attention Mechanism (Bahdanau/Luong) | Lets the model focus on relevant input parts | [Watch](https://www.youtube.com/results?search_query=Attention%20Mechanism%20%28Bahdanau/Luong%29%20explained) |
| 18 | Transformer | Attention-only architecture, backbone of modern NLP/vision models | [Watch](https://www.youtube.com/results?search_query=Transformer%20explained) |
| 19 | BERT | Bidirectional transformer for language understanding | [Watch](https://www.youtube.com/results?search_query=BERT%20explained) |
| 20 | GPT family | Autoregressive transformer for language generation | [Watch](https://www.youtube.com/results?search_query=GPT%20family%20explained) |
| 21 | T5 | Transformer that frames all NLP tasks as text-to-text | [Watch](https://www.youtube.com/results?search_query=T5%20explained) |
| 22 | Vision Transformer (ViT) | Applies transformer attention directly to image patches | [Watch](https://www.youtube.com/results?search_query=Vision%20Transformer%20%28ViT%29%20explained) |
| 23 | Autoencoder (AE) | Compress and reconstruct data to learn efficient representations | [Watch](https://www.youtube.com/results?search_query=Autoencoder%20%28AE%29%20explained) |
| 24 | Variational Autoencoder (VAE) | Probabilistic autoencoder for generating new data | [Watch](https://www.youtube.com/results?search_query=Variational%20Autoencoder%20%28VAE%29%20explained) |
| 25 | GAN | Generator vs. discriminator trained adversarially to create realistic data | [Watch](https://www.youtube.com/results?search_query=GAN%20explained) |
| 26 | DCGAN | GAN using convolutional layers for image generation | [Watch](https://www.youtube.com/results?search_query=DCGAN%20explained) |
| 27 | CycleGAN | Translate images between two domains without paired examples | [Watch](https://www.youtube.com/results?search_query=CycleGAN%20explained) |
| 28 | StyleGAN | GAN with style-based control over generated image features | [Watch](https://www.youtube.com/results?search_query=StyleGAN%20explained) |
| 29 | WGAN | GAN variant with a more stable training loss (Wasserstein distance) | [Watch](https://www.youtube.com/results?search_query=WGAN%20explained) |
| 30 | Diffusion Models (DDPM, Stable Diffusion) | Generate data by reversing a noise process | [Watch](https://www.youtube.com/results?search_query=Diffusion%20Models%20%28DDPM%2C%20Stable%20Diffusion%29%20explained) |
| 31 | GCN | Apply convolutions over graph-structured data | [Watch](https://www.youtube.com/results?search_query=GCN%20explained) |
| 32 | GraphSAGE | Generate node embeddings by sampling and aggregating neighbors | [Watch](https://www.youtube.com/results?search_query=GraphSAGE%20explained) |
| 33 | GAT | Graph network that weighs neighbor importance via attention | [Watch](https://www.youtube.com/results?search_query=GAT%20explained) |
| 34 | DQN | Deep Q-learning for decision-making from raw states | [Watch](https://www.youtube.com/results?search_query=DQN%20explained) |
| 35 | Policy Gradient | Directly optimize a policy for expected reward | [Watch](https://www.youtube.com/results?search_query=Policy%20Gradient%20explained) |
| 36 | Actor-Critic (A2C/A3C) | Combine value estimation (critic) with policy learning (actor) | [Watch](https://www.youtube.com/results?search_query=Actor-Critic%20%28A2C/A3C%29%20explained) |
| 37 | PPO | Stable, clipped policy-gradient method for reinforcement learning | [Watch](https://www.youtube.com/results?search_query=PPO%20explained) |
| 38 | Dropout | Randomly disable neurons during training to prevent overfitting | [Watch](https://www.youtube.com/results?search_query=Dropout%20explained) |
| 39 | Batch Normalization | Normalize layer inputs to stabilize/speed up training | [Watch](https://www.youtube.com/results?search_query=Batch%20Normalization%20explained) |
| 40 | Layer Normalization | Normalize across features per sample, common in transformers | [Watch](https://www.youtube.com/results?search_query=Layer%20Normalization%20explained) |
| 41 | SGD | Update weights using gradient of small data batches | [Watch](https://www.youtube.com/results?search_query=SGD%20explained) |
| 42 | Momentum | Accelerate SGD by accumulating past gradients | [Watch](https://www.youtube.com/results?search_query=Momentum%20explained) |
| 43 | RMSProp | Adapt learning rate per parameter using recent gradient magnitude | [Watch](https://www.youtube.com/results?search_query=RMSProp%20explained) |
| 44 | Adam | Combines momentum and adaptive learning rates for fast convergence | [Watch](https://www.youtube.com/results?search_query=Adam%20explained) |
| 45 | AdamW | Adam with decoupled weight decay for better generalization | [Watch](https://www.youtube.com/results?search_query=AdamW%20explained) |
| 46 | Restricted Boltzmann Machine (RBM) | Learn a probability distribution over inputs using a two-layer stochastic network | [Watch](https://www.youtube.com/results?search_query=Restricted%20Boltzmann%20Machine%20%28RBM%29%20explained) |
| 47 | Deep Belief Network (DBN) | Stack multiple RBMs to learn hierarchical feature representations | [Watch](https://www.youtube.com/results?search_query=Deep%20Belief%20Network%20%28DBN%29%20explained) |
| 48 | Hopfield Network | Recurrent network that stores patterns as stable states for associative memory recall | [Watch](https://www.youtube.com/results?search_query=Hopfield%20Network%20explained) |
| 49 | Siamese Networks | Compare two inputs using twin networks with shared weights, useful for similarity/verification | [Watch](https://www.youtube.com/results?search_query=Siamese%20Networks%20explained) |
| 50 | Capsule Networks | Preserve spatial hierarchies between features using vector-based capsules instead of scalar neurons | [Watch](https://www.youtube.com/results?search_query=Capsule%20Networks%20explained) |
| 51 | Highway Networks | Use gated skip connections to let deep networks train more easily, precursor to ResNet | [Watch](https://www.youtube.com/results?search_query=Highway%20Networks%20explained) |

</details>


<details>
<summary><h2>10. Computer Vision</h2></summary>

**Why here:** These are DL architectures specialized for images — you need to understand CNNs (from Deep Learning) before understanding detection (YOLO) or segmentation (U-Net) built on top of them.

**Unlocks:** Image-specific tasks: classification, detection, segmentation, generation.

**Reference:**
- Book: "Computer Vision: Algorithms and Applications" by Richard Szeliski
- Site: https://cs231n.stanford.edu/
- Site: https://pyimagesearch.com/

| S.No | Algorithm | Description | YouTube |
|---|---|---|---|
| 1 | CNN Classifiers (AlexNet/VGG/ResNet/EfficientNet) | Assign a label to an entire image | [Watch](https://www.youtube.com/results?search_query=CNN%20Classifiers%20%28AlexNet/VGG/ResNet/EfficientNet%29%20explained) |
| 2 | ViT (vision use) | Classify images using transformer attention over patches | [Watch](https://www.youtube.com/results?search_query=ViT%20%28vision%20use%29%20explained) |
| 3 | R-CNN | Propose regions then classify each for object detection | [Watch](https://www.youtube.com/results?search_query=R-CNN%20explained) |
| 4 | Fast R-CNN | Faster region-based detection by sharing CNN features | [Watch](https://www.youtube.com/results?search_query=Fast%20R-CNN%20explained) |
| 5 | Faster R-CNN | Adds a learned region proposal network for speed | [Watch](https://www.youtube.com/results?search_query=Faster%20R-CNN%20explained) |
| 6 | YOLO | Detect all objects in one pass for real-time speed | [Watch](https://www.youtube.com/results?search_query=YOLO%20explained) |
| 7 | SSD | Single-shot multi-scale object detection | [Watch](https://www.youtube.com/results?search_query=SSD%20explained) |
| 8 | RetinaNet | Detector using focal loss to handle class imbalance | [Watch](https://www.youtube.com/results?search_query=RetinaNet%20explained) |
| 9 | DETR | Transformer-based end-to-end object detection | [Watch](https://www.youtube.com/results?search_query=DETR%20explained) |
| 10 | FCN | Fully convolutional network for pixel-wise segmentation | [Watch](https://www.youtube.com/results?search_query=FCN%20explained) |
| 11 | U-Net | Encoder-decoder segmentation network, strong for medical images | [Watch](https://www.youtube.com/results?search_query=U-Net%20explained) |
| 12 | DeepLab | Segmentation using dilated convolutions for context | [Watch](https://www.youtube.com/results?search_query=DeepLab%20explained) |
| 13 | SegNet | Encoder-decoder segmentation using pooling indices | [Watch](https://www.youtube.com/results?search_query=SegNet%20explained) |
| 14 | Mask R-CNN | Detect objects and generate per-instance segmentation masks | [Watch](https://www.youtube.com/results?search_query=Mask%20R-CNN%20explained) |
| 15 | Panoptic FPN | Combines semantic + instance segmentation into one output | [Watch](https://www.youtube.com/results?search_query=Panoptic%20FPN%20explained) |
| 16 | SIFT | Detect scale/rotation-invariant keypoints for matching | [Watch](https://www.youtube.com/results?search_query=SIFT%20explained) |
| 17 | SURF | Faster approximation of SIFT for keypoint detection | [Watch](https://www.youtube.com/results?search_query=SURF%20explained) |
| 18 | ORB | Fast, free alternative to SIFT/SURF for keypoint matching | [Watch](https://www.youtube.com/results?search_query=ORB%20explained) |
| 19 | HOG | Describe image gradients, classic for pedestrian/object detection | [Watch](https://www.youtube.com/results?search_query=HOG%20explained) |
| 20 | Canny Edge Detection | Detect edges via gradient intensity changes | [Watch](https://www.youtube.com/results?search_query=Canny%20Edge%20Detection%20explained) |
| 21 | Harris Corner Detection | Detect corner points in an image | [Watch](https://www.youtube.com/results?search_query=Harris%20Corner%20Detection%20explained) |
| 22 | Pix2Pix | Translate one image type to another using paired data (GAN) | [Watch](https://www.youtube.com/results?search_query=Pix2Pix%20explained) |
| 23 | CycleGAN (vision use) | Translate images between domains without paired data | [Watch](https://www.youtube.com/results?search_query=CycleGAN%20%28vision%20use%29%20explained) |
| 24 | StyleGAN (vision use) | Generate high-quality synthetic images with style control | [Watch](https://www.youtube.com/results?search_query=StyleGAN%20%28vision%20use%29%20explained) |
| 25 | Super-Resolution GAN | Upscale low-resolution images with realistic detail | [Watch](https://www.youtube.com/results?search_query=Super-Resolution%20GAN%20explained) |
| 26 | Stable Diffusion / DALL·E | Generate images from text prompts | [Watch](https://www.youtube.com/results?search_query=Stable%20Diffusion%20/%20DALL%C2%B7E%20explained) |
| 27 | OpenPose | Estimate human body keypoints/pose from images | [Watch](https://www.youtube.com/results?search_query=OpenPose%20explained) |
| 28 | HRNet | Maintain high-resolution features for accurate pose estimation | [Watch](https://www.youtube.com/results?search_query=HRNet%20explained) |
| 29 | FaceNet | Map faces to embeddings for recognition/verification | [Watch](https://www.youtube.com/results?search_query=FaceNet%20explained) |
| 30 | DeepFace | Deep learning pipeline for face verification | [Watch](https://www.youtube.com/results?search_query=DeepFace%20explained) |
| 31 | ArcFace | Face recognition using angular margin loss for better separation | [Watch](https://www.youtube.com/results?search_query=ArcFace%20explained) |
| 32 | Lucas-Kanade | Estimate optical flow (motion) between frames | [Watch](https://www.youtube.com/results?search_query=Lucas-Kanade%20explained) |
| 33 | FlowNet | Deep learning-based optical flow estimation | [Watch](https://www.youtube.com/results?search_query=FlowNet%20explained) |
| 34 | SORT | Simple, fast multi-object tracking using Kalman filter + IOU | [Watch](https://www.youtube.com/results?search_query=SORT%20explained) |
| 35 | DeepSORT | SORT enhanced with a deep appearance embedding for tracking | [Watch](https://www.youtube.com/results?search_query=DeepSORT%20explained) |
| 36 | Kalman Filter | Predict/track object position under uncertainty over time | [Watch](https://www.youtube.com/results?search_query=Kalman%20Filter%20explained) |
| 37 | Neural Style Transfer | Blend the content of one image with the artistic style of another using CNN features | [Watch](https://www.youtube.com/results?search_query=Neural%20Style%20Transfer%20explained) |
| 38 | Image Captioning (CNN+RNN/Transformer) | Generate a natural language description of an image's content | [Watch](https://www.youtube.com/results?search_query=Image%20Captioning%20%28CNN%2BRNN/Transformer%29%20explained) |
| 39 | Depth Estimation (MiDaS) | Predict per-pixel depth from a single 2D image | [Watch](https://www.youtube.com/results?search_query=Depth%20Estimation%20%28MiDaS%29%20explained) |
| 40 | PointNet | Directly process 3D point cloud data for classification/segmentation | [Watch](https://www.youtube.com/results?search_query=PointNet%20explained) |
| 41 | 3D CNN / SlowFast | Recognize actions in video by learning spatio-temporal features | [Watch](https://www.youtube.com/results?search_query=3D%20CNN%20/%20SlowFast%20explained) |
| 42 | Swin Transformer | Vision transformer using shifted windows for efficient hierarchical feature extraction | [Watch](https://www.youtube.com/results?search_query=Swin%20Transformer%20explained) |
| 43 | ConvNeXt | Modernized pure-CNN architecture that matches transformer-level accuracy | [Watch](https://www.youtube.com/results?search_query=ConvNeXt%20explained) |
| 44 | Image Inpainting | Fill in missing or removed regions of an image realistically | [Watch](https://www.youtube.com/results?search_query=Image%20Inpainting%20explained) |

</details>


<details>
<summary><h2>11. NLP-specific</h2></summary>

**Why here:** Transformers (from Deep Learning) are the backbone; this stage applies them specifically to text.

**Unlocks:** Text-specific tasks: embeddings, entity recognition, topic modeling.

**Reference:**
- Book: "Speech and Language Processing" by Jurafsky & Martin
- Site: https://web.stanford.edu/~jurafsky/slp3/
- Site: https://huggingface.co/learn/nlp-course

| S.No | Algorithm | Description | YouTube |
|---|---|---|---|
| 1 | TF-IDF | Weigh words by importance across a document collection | [Watch](https://www.youtube.com/results?search_query=TF-IDF%20explained) |
| 2 | Word2Vec | Learn dense word embeddings from context | [Watch](https://www.youtube.com/results?search_query=Word2Vec%20explained) |
| 3 | GloVe | Learn word embeddings from global co-occurrence statistics | [Watch](https://www.youtube.com/results?search_query=GloVe%20explained) |
| 4 | FastText | Word embeddings that also capture subword information | [Watch](https://www.youtube.com/results?search_query=FastText%20explained) |
| 5 | Named Entity Recognition (NER) | Identify names, places, orgs, etc. in text | [Watch](https://www.youtube.com/results?search_query=Named%20Entity%20Recognition%20%28NER%29%20explained) |
| 6 | Topic Modeling (LDA, text) | Discover latent topics across documents | [Watch](https://www.youtube.com/results?search_query=Topic%20Modeling%20%28LDA%2C%20text%29%20explained) |
| 7 | POS Tagging | Label each word with its grammatical role | [Watch](https://www.youtube.com/results?search_query=POS%20Tagging%20explained) |

</details>


<details>
<summary><h2>12. Time Series</h2></summary>

**Why here:** Statistical forecasting (ARIMA) can be learned early, but LSTM-based forecasting depends on understanding RNN/LSTM from Deep Learning.

**Unlocks:** The ability to forecast sequences with trend and seasonality.

**Reference:**
- Book: "Forecasting: Principles and Practice" by Hyndman & Athanasopoulos
- Site: https://otexts.com/fpp3/
- Site: https://facebook.github.io/prophet/

| S.No | Algorithm | Description | YouTube |
|---|---|---|---|
| 1 | ARIMA | Forecast based on autoregression, differencing, and moving average | [Watch](https://www.youtube.com/results?search_query=ARIMA%20explained) |
| 2 | SARIMA | ARIMA extended to handle seasonality | [Watch](https://www.youtube.com/results?search_query=SARIMA%20explained) |
| 3 | Prophet | Forecasting model handling trend, seasonality, and holidays automatically | [Watch](https://www.youtube.com/results?search_query=Prophet%20explained) |
| 4 | Exponential Smoothing (Holt-Winters) | Weight recent observations more for forecasting | [Watch](https://www.youtube.com/results?search_query=Exponential%20Smoothing%20%28Holt-Winters%29%20explained) |
| 5 | LSTM/GRU for Forecasting | Capture long-range temporal patterns for prediction | [Watch](https://www.youtube.com/results?search_query=LSTM/GRU%20for%20Forecasting%20explained) |
| 6 | Moving Average | Smooth a series to reveal underlying trend | [Watch](https://www.youtube.com/results?search_query=Moving%20Average%20explained) |

</details>


<details>
<summary><h2>13. Recommendation Systems</h2></summary>

**Why here:** Basic collaborative filtering is classical, but Neural Collaborative Filtering needs neural network fundamentals from Deep Learning.

**Unlocks:** Personalized recommendations combining classical and neural approaches.

**Reference:**
- Book: "Recommender Systems: The Textbook" by Charu Aggarwal
- Site: https://developers.google.com/machine-learning/recommendation

| S.No | Algorithm | Description | YouTube |
|---|---|---|---|
| 1 | Collaborative Filtering | Recommend based on similar users'/items' behavior | [Watch](https://www.youtube.com/results?search_query=Collaborative%20Filtering%20explained) |
| 2 | Matrix Factorization (SVD-based) | Learn latent user/item factors from ratings | [Watch](https://www.youtube.com/results?search_query=Matrix%20Factorization%20%28SVD-based%29%20explained) |
| 3 | Content-Based Filtering | Recommend items similar to what a user already liked | [Watch](https://www.youtube.com/results?search_query=Content-Based%20Filtering%20explained) |
| 4 | Neural Collaborative Filtering | Learn user-item interactions with a neural network | [Watch](https://www.youtube.com/results?search_query=Neural%20Collaborative%20Filtering%20explained) |
| 5 | Hybrid Recommender | Combine collaborative + content-based signals | [Watch](https://www.youtube.com/results?search_query=Hybrid%20Recommender%20explained) |

</details>


<details>
<summary><h2>14. Explainability (XAI)</h2></summary>

**Why here:** You can only explain a model once it's complex enough to need explaining — Grad-CAM specifically requires a trained CNN to visualize.

**Unlocks:** The ability to interpret and trust complex model decisions.

**Reference:**
- Book: "Interpretable Machine Learning" by Christoph Molnar (free online)
- Site: https://christophm.github.io/interpretable-ml-book/
- Site: https://shap.readthedocs.io/

| S.No | Algorithm | Description | YouTube |
|---|---|---|---|
| 1 | SHAP | Explain individual predictions by attributing contribution to each feature | [Watch](https://www.youtube.com/results?search_query=SHAP%20explained) |
| 2 | LIME | Approximate a complex model locally with an interpretable one to explain a prediction | [Watch](https://www.youtube.com/results?search_query=LIME%20explained) |
| 3 | Grad-CAM | Highlight image regions a CNN used to make its prediction | [Watch](https://www.youtube.com/results?search_query=Grad-CAM%20explained) |
| 4 | Integrated Gradients | Attribute a deep model's prediction to input features via gradient path integration | [Watch](https://www.youtube.com/results?search_query=Integrated%20Gradients%20explained) |
| 5 | Permutation Feature Importance | Measure feature importance by shuffling it and seeing performance drop | [Watch](https://www.youtube.com/results?search_query=Permutation%20Feature%20Importance%20explained) |
| 6 | Partial Dependence Plot (PDP) | Show how a feature affects predictions on average, holding others fixed | [Watch](https://www.youtube.com/results?search_query=Partial%20Dependence%20Plot%20%28PDP%29%20explained) |

</details>


<details>
<summary><h2>15. Transfer Learning / Fine-Tuning</h2></summary>

**Why here:** Requires a pretrained deep model to already exist (from Deep Learning, CV, NLP) before you can reuse or adapt it.

**Unlocks:** Faster, cheaper model development by reusing existing knowledge.

**Reference:**
- Site: https://huggingface.co/docs/transformers/training
- Site: https://cs231n.github.io/transfer-learning/

| S.No | Algorithm | Description | YouTube |
|---|---|---|---|
| 1 | Transfer Learning (feature extraction) | Reuse a pretrained model's learned features for a new, related task | [Watch](https://www.youtube.com/results?search_query=Transfer%20Learning%20%28feature%20extraction%29%20explained) |
| 2 | Fine-Tuning | Continue training a pretrained model's weights on new task-specific data | [Watch](https://www.youtube.com/results?search_query=Fine-Tuning%20explained) |
| 3 | Domain Adaptation | Adapt a model trained on one data distribution to perform well on another | [Watch](https://www.youtube.com/results?search_query=Domain%20Adaptation%20explained) |
| 4 | LoRA (Low-Rank Adaptation) | Fine-tune large models efficiently by training small low-rank weight updates | [Watch](https://www.youtube.com/results?search_query=LoRA%20%28Low-Rank%20Adaptation%29%20explained) |

</details>


<details>
<summary><h2>16. Self-Supervised / Contrastive Learning</h2></summary>

**Why here:** This is an advanced pretraining strategy for deep models — you need to fully understand supervised DL first to appreciate why learning without labels is different/harder.

**Unlocks:** The ability to pretrain models without labeled data.

**Reference:**
- Site: https://lilianweng.github.io/posts/2019-11-10-self-supervised/
- Site: https://ai.meta.com/blog/self-supervised-learning-the-dark-matter-of-intelligence/

| S.No | Algorithm | Description | YouTube |
|---|---|---|---|
| 1 | SimCLR | Learn representations by contrasting augmented views of the same image | [Watch](https://www.youtube.com/results?search_query=SimCLR%20explained) |
| 2 | MoCo (Momentum Contrast) | Contrastive learning using a momentum-updated memory queue of negatives | [Watch](https://www.youtube.com/results?search_query=MoCo%20%28Momentum%20Contrast%29%20explained) |
| 3 | BYOL | Learn representations without negative samples using two networks that predict each other | [Watch](https://www.youtube.com/results?search_query=BYOL%20explained) |
| 4 | Masked Autoencoders (MAE) | Learn representations by reconstructing randomly masked parts of input | [Watch](https://www.youtube.com/results?search_query=Masked%20Autoencoders%20%28MAE%29%20explained) |

</details>


<details>
<summary><h2>17. AutoML</h2></summary>

**Why here:** AutoML automates everything above — model selection, tuning, architecture search. It only makes sense once you understand what's being automated.

**Unlocks:** Automated pipelines that replace manual trial-and-error across every stage above.

**Reference:**
- Book: "Automated Machine Learning" by Hutter, Kotthoff, Vanschoren (free online)
- Site: https://www.automl.org/book/

| S.No | Algorithm | Description | YouTube |
|---|---|---|---|
| 1 | Neural Architecture Search (NAS) | Automatically search for the best neural network architecture | [Watch](https://www.youtube.com/results?search_query=Neural%20Architecture%20Search%20%28NAS%29%20explained) |
| 2 | Auto-sklearn | Automatically select and tune classical ML models/pipelines | [Watch](https://www.youtube.com/results?search_query=Auto-sklearn%20explained) |
| 3 | TPOT | Use genetic programming to automatically build ML pipelines | [Watch](https://www.youtube.com/results?search_query=TPOT%20explained) |
| 4 | Google AutoML / H2O AutoML | Automate model selection, tuning, and training end-to-end | [Watch](https://www.youtube.com/results?search_query=Google%20AutoML%20/%20H2O%20AutoML%20explained) |

</details>
