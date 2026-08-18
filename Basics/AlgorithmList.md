# Algorithms Reference: EDA, Deep Learning, Computer Vision

<details>
<summary><h2>Exploratory Data Analysis (EDA)</h2></summary>

**Univariate Analysis**
- Histogram, Box Plot, Violin Plot
- Distribution fitting (Normal, Poisson, Binomial checks)
- Skewness & Kurtosis analysis
- Q-Q Plot (normality check)

**Bivariate/Multivariate Analysis**
- Correlation analysis (Pearson, Spearman, Kendall)
- Scatter plots, Pair plots
- Cross-tabulation / Chi-Square test
- Covariance matrix
- Heatmaps

**Dimensionality Reduction (EDA/Preprocessing)**
- PCA (Principal Component Analysis)
- t-SNE
- UMAP
- LDA (Linear Discriminant Analysis)
- Factor Analysis
- SVD (Singular Value Decomposition)

**Outlier Detection**
- Z-Score method
- IQR (Interquartile Range) method
- Isolation Forest
- Local Outlier Factor (LOF)
- DBSCAN-based outlier detection

**Missing Value Analysis**
- Missing pattern visualization (matrix, heatmap)
- Imputation strategies (mean/median/mode, KNN imputer, MICE)

**Clustering (used in EDA)**
- K-Means
- Hierarchical Clustering
- DBSCAN
- Gaussian Mixture Models (GMM)

**Feature Analysis**
- Feature Importance (via tree-based models)
- Mutual Information
- Variance Threshold
- ANOVA F-test

</details>

<details>
<summary><h2>Time Series</h2></summary>

- ARIMA
- SARIMA
- Prophet
- Exponential Smoothing (Holt-Winters)
- LSTM/GRU for forecasting
- Moving Average / Weighted Moving Average

</details>

<details>
<summary><h2>NLP-specific</h2></summary>

- TF-IDF
- Word2Vec
- GloVe
- FastText
- Named Entity Recognition (NER) models
- Topic Modeling (LDA — text version)
- POS Tagging models

</details>

<details>
<summary><h2>Recommendation Systems</h2></summary>

- Collaborative Filtering
- Matrix Factorization (SVD-based)
- Content-Based Filtering
- Neural Collaborative Filtering
- Hybrid Recommender Systems

</details>

<details>
<summary><h2>Ensemble / Classical ML</h2></summary>

**Bagging-based**
- Random Forest
- Bagging (Bootstrap Aggregating)
- Extra Trees (Extremely Randomized Trees)

**Boosting-based**
- AdaBoost
- Gradient Boosting (GBM)
- XGBoost
- LightGBM
- CatBoost

**Stacking-based**
- Stacked Generalization (Stacking)
- Blending

**Base Learners (commonly used in EDA/baseline modeling)**
- Decision Tree
- Linear Regression / Logistic Regression
- K-Nearest Neighbors (KNN)
- Support Vector Machine (SVM)
- Naive Bayes

</details>

<details>
<summary><h2>Deep Learning</h2></summary>

**Foundational Architectures**
- Perceptron
- Multi-Layer Perceptron (MLP) / Feedforward Neural Network (FNN)

**Convolutional Networks (CNN family)**
- LeNet
- AlexNet
- VGG
- GoogLeNet (Inception)
- ResNet (Residual Networks)
- DenseNet
- EfficientNet
- MobileNet
- Xception

**Recurrent Networks (Sequence Models)**
- RNN (Vanilla)
- LSTM (Long Short-Term Memory)
- GRU (Gated Recurrent Unit)
- Bidirectional RNN/LSTM
- Seq2Seq (Encoder-Decoder)

**Attention & Transformers**
- Attention Mechanism (Bahdanau, Luong)
- Transformer
- BERT
- GPT family
- T5
- Vision Transformer (ViT) — bridges into vision too

**Generative Models**
- Autoencoder (AE)
- Variational Autoencoder (VAE)
- GAN (Generative Adversarial Network) and variants (DCGAN, CycleGAN, StyleGAN, WGAN)
- Diffusion Models (DDPM, Stable Diffusion)

**Graph-based**
- GCN (Graph Convolutional Network)
- GraphSAGE
- GAT (Graph Attention Network)

**Reinforcement Learning (Deep RL)**
- DQN (Deep Q-Network)
- Policy Gradient
- Actor-Critic (A2C, A3C)
- PPO (Proximal Policy Optimization)

**Regularization/Optimization Techniques**
- Dropout
- Batch Normalization
- Layer Normalization
- Optimizers: SGD, Momentum, RMSProp, Adam, AdamW

</details>

<details>
<summary><h2>Computer Vision</h2></summary>

**Classification**
- CNN-based classifiers (AlexNet, VGG, ResNet, EfficientNet)
- ViT (Vision Transformer)

**Object Detection**
- R-CNN
- Fast R-CNN
- Faster R-CNN
- YOLO (v1 through latest)
- SSD (Single Shot Detector)
- RetinaNet
- DETR (Detection Transformer)

**Image Segmentation**
- Semantic Segmentation: FCN, U-Net, DeepLab (v1–v3+), SegNet
- Instance Segmentation: Mask R-CNN
- Panoptic Segmentation: Panoptic FPN

**Feature Extraction/Matching (Classical CV)**
- SIFT (Scale-Invariant Feature Transform)
- SURF (Speeded-Up Robust Features)
- ORB (Oriented FAST and Rotated BRIEF)
- HOG (Histogram of Oriented Gradients)
- Canny Edge Detection
- Harris Corner Detection

**Image Generation/Enhancement**
- GAN variants for vision (Pix2Pix, CycleGAN, StyleGAN, Super-Resolution GAN)
- Diffusion models (Stable Diffusion, DALL·E)

**Pose Estimation**
- OpenPose
- HRNet (High-Resolution Network)

**Face Recognition**
- FaceNet
- DeepFace
- ArcFace

**Optical Flow / Motion**
- Lucas-Kanade
- FlowNet

**Tracking**
- SORT / DeepSORT
- Kalman Filter (classical, still widely used)

</details>
