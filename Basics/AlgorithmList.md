# Master Algorithm Reference: EDA, ML, Deep Learning, Computer Vision

Numbered continuously across the whole document. Each entry: **what it's useful for**.

<details>
<summary><h2>1. Exploratory Data Analysis (EDA)</h2></summary>

1. Histogram — visualize the distribution shape of a single variable
2. Box Plot — show median, quartiles, and outliers at a glance
3. Violin Plot — combine box plot with distribution density
4. Q-Q Plot — check whether data follows a normal distribution
5. Skewness & Kurtosis — measure asymmetry and tail-heaviness of a distribution
6. Correlation Analysis (Pearson/Spearman/Kendall) — measure strength/direction of relationship between two variables
7. Scatter Plot / Pair Plot — visualize relationships between variable pairs
8. Cross-tabulation / Chi-Square Test — test relationship between two categorical variables
9. Covariance Matrix — measure how variables vary together
10. Heatmap — visualize a correlation/matrix using color intensity
11. PCA — reduce dimensions while keeping maximum variance
12. t-SNE — visualize high-dimensional data in 2D/3D preserving local structure
13. UMAP — faster nonlinear dimensionality reduction preserving local + global structure
14. LDA (dimensionality) — reduce dimensions while maximizing class separability
15. Factor Analysis — find hidden (latent) variables explaining correlations
16. SVD — decompose a matrix for compression/dimensionality reduction
17. Z-Score Method — flag outliers based on standard deviations from mean
18. IQR Method — flag outliers using the interquartile range
19. Isolation Forest — detect anomalies by how easily a point gets isolated
20. Local Outlier Factor (LOF) — detect outliers via local density deviation
21. DBSCAN (outlier use) — flag points that don't belong to any dense region
22. Missing Pattern Visualization — spot patterns in where data is missing
23. Mean/Median/Mode Imputation — fill missing values with central tendency
24. KNN Imputer — fill missing values using nearest neighbors' values
25. MICE — iteratively impute missing values using regression chains
26. K-Means — partition data into K groups by similarity
27. Hierarchical Clustering — build nested clusters shown as a dendrogram
28. DBSCAN (clustering use) — cluster by density, handles irregular shapes
29. Gaussian Mixture Model (GMM) — soft/probabilistic clustering
30. Feature Importance (tree-based) — rank features by predictive contribution
31. Mutual Information — measure dependency between a feature and the target
32. Variance Threshold — drop low-variance, uninformative features
33. ANOVA F-test — test if a feature's mean differs significantly across groups

</details>

<details>
<summary><h2>2. Ensemble / Classical ML</h2></summary>

34. Decision Tree — split data on feature thresholds to predict a label/value
35. Linear Regression — predict a continuous value from a linear combination of features
36. Logistic Regression — predict a class probability using a linear decision boundary
37. K-Nearest Neighbors (KNN) — classify/predict based on the closest training examples
38. Support Vector Machine (SVM) — find the maximum-margin boundary between classes
39. Naive Bayes — classify using Bayes' theorem assuming feature independence
40. Random Forest — average many decision trees (bagging) to reduce variance
41. Bagging — train models on random data subsets and average results
42. Extra Trees — like Random Forest but with extra randomness in splits, faster
43. AdaBoost — sequentially boost weak learners by reweighting misclassified points
44. Gradient Boosting (GBM) — sequentially fit models to the residual errors
45. XGBoost — regularized, optimized gradient boosting for speed and accuracy
46. LightGBM — leaf-wise gradient boosting, very fast on large datasets
47. CatBoost — gradient boosting optimized for categorical features
48. Stacking — combine multiple models' predictions using a meta-model
49. Blending — like stacking but meta-model trained on a held-out validation set

</details>

<details>
<summary><h2>3. Deep Learning</h2></summary>

50. Perceptron — the single-neuron building block of neural networks
51. Multi-Layer Perceptron (MLP) — stack of fully connected layers for general prediction
52. LeNet — early CNN for simple digit/image recognition
53. AlexNet — deeper CNN that popularized deep learning for image classification
54. VGG — very deep CNN using small stacked filters
55. GoogLeNet (Inception) — CNN using parallel multi-scale filters for efficiency
56. ResNet — CNN with skip connections to train very deep networks
57. DenseNet — CNN where each layer connects to all previous layers
58. EfficientNet — CNN scaled systematically for accuracy vs. compute tradeoff
59. MobileNet — lightweight CNN designed for mobile/edge devices
60. Xception — CNN using depthwise separable convolutions for efficiency
61. RNN — processes sequences by passing a hidden state forward in time
62. LSTM — RNN variant that handles long-term dependencies via gates
63. GRU — simplified LSTM with fewer gates, faster to train
64. Bidirectional RNN/LSTM — reads sequence both forward and backward for context
65. Seq2Seq (Encoder-Decoder) — maps an input sequence to an output sequence
66. Attention Mechanism (Bahdanau/Luong) — lets the model focus on relevant input parts
67. Transformer — attention-only architecture, backbone of modern NLP/vision models
68. BERT — bidirectional transformer for language understanding
69. GPT family — autoregressive transformer for language generation
70. T5 — transformer that frames all NLP tasks as text-to-text
71. Vision Transformer (ViT) — applies transformer attention directly to image patches
72. Autoencoder (AE) — compress and reconstruct data to learn efficient representations
73. Variational Autoencoder (VAE) — probabilistic autoencoder for generating new data
74. GAN — generator vs. discriminator trained adversarially to create realistic data
75. DCGAN — GAN using convolutional layers for image generation
76. CycleGAN — translate images between two domains without paired examples
77. StyleGAN — GAN with style-based control over generated image features
78. WGAN — GAN variant with a more stable training loss (Wasserstein distance)
79. Diffusion Models (DDPM, Stable Diffusion) — generate data by reversing a noise process
80. GCN — apply convolutions over graph-structured data
81. GraphSAGE — generate node embeddings by sampling and aggregating neighbors
82. GAT — graph network that weighs neighbor importance via attention
83. DQN — deep Q-learning for decision-making from raw states
84. Policy Gradient — directly optimize a policy for expected reward
85. Actor-Critic (A2C/A3C) — combine value estimation (critic) with policy learning (actor)
86. PPO — stable, clipped policy-gradient method for reinforcement learning
87. Dropout — randomly disable neurons during training to prevent overfitting
88. Batch Normalization — normalize layer inputs to stabilize/speed up training
89. Layer Normalization — normalize across features per sample, common in transformers
90. SGD — update weights using gradient of small data batches
91. Momentum — accelerate SGD by accumulating past gradients
92. RMSProp — adapt learning rate per parameter using recent gradient magnitude
93. Adam — combines momentum and adaptive learning rates for fast convergence
94. AdamW — Adam with decoupled weight decay for better generalization

</details>

<details>
<summary><h2>4. Computer Vision</h2></summary>

95. CNN Classifiers (AlexNet/VGG/ResNet/EfficientNet) — assign a label to an entire image
96. ViT (vision use) — classify images using transformer attention over patches
97. R-CNN — propose regions then classify each for object detection
98. Fast R-CNN — faster region-based detection by sharing CNN features
99. Faster R-CNN — adds a learned region proposal network for speed
100. YOLO — detect all objects in one pass for real-time speed
101. SSD — single-shot multi-scale object detection
102. RetinaNet — detector using focal loss to handle class imbalance
103. DETR — transformer-based end-to-end object detection
104. FCN — fully convolutional network for pixel-wise segmentation
105. U-Net — encoder-decoder segmentation network, strong for medical images
106. DeepLab — segmentation using dilated convolutions for context
107. SegNet — encoder-decoder segmentation using pooling indices
108. Mask R-CNN — detect objects and generate per-instance segmentation masks
109. Panoptic FPN — combines semantic + instance segmentation into one output
110. SIFT — detect scale/rotation-invariant keypoints for matching
111. SURF — faster approximation of SIFT for keypoint detection
112. ORB — fast, free alternative to SIFT/SURF for keypoint matching
113. HOG — describe image gradients, classic for pedestrian/object detection
114. Canny Edge Detection — detect edges via gradient intensity changes
115. Harris Corner Detection — detect corner points in an image
116. Pix2Pix — translate one image type to another using paired data (GAN)
117. CycleGAN (vision use) — translate images between domains without paired data
118. StyleGAN (vision use) — generate high-quality synthetic images with style control
119. Super-Resolution GAN — upscale low-resolution images with realistic detail
120. Stable Diffusion / DALL·E — generate images from text prompts
121. OpenPose — estimate human body keypoints/pose from images
122. HRNet — maintain high-resolution features for accurate pose estimation
123. FaceNet — map faces to embeddings for recognition/verification
124. DeepFace — deep learning pipeline for face verification
125. ArcFace — face recognition using angular margin loss for better separation
126. Lucas-Kanade — estimate optical flow (motion) between frames
127. FlowNet — deep learning-based optical flow estimation
128. SORT — simple, fast multi-object tracking using Kalman filter + IOU
129. DeepSORT — SORT enhanced with a deep appearance embedding for tracking
130. Kalman Filter — predict/track object position under uncertainty over time

</details>

<details>
<summary><h2>5. Time Series</h2></summary>

131. ARIMA — forecast based on autoregression, differencing, and moving average
132. SARIMA — ARIMA extended to handle seasonality
133. Prophet — forecasting model handling trend, seasonality, and holidays automatically
134. Exponential Smoothing (Holt-Winters) — weight recent observations more for forecasting
135. LSTM/GRU for Forecasting — capture long-range temporal patterns for prediction
136. Moving Average — smooth a series to reveal underlying trend

</details>

<details>
<summary><h2>6. NLP-specific</h2></summary>

137. TF-IDF — weigh words by importance across a document collection
138. Word2Vec — learn dense word embeddings from context
139. GloVe — learn word embeddings from global co-occurrence statistics
140. FastText — word embeddings that also capture subword information
141. Named Entity Recognition (NER) — identify names, places, orgs, etc. in text
142. Topic Modeling (LDA, text) — discover latent topics across documents
143. POS Tagging — label each word with its grammatical role

</details>

<details>
<summary><h2>7. Recommendation Systems</h2></summary>

144. Collaborative Filtering — recommend based on similar users'/items' behavior
145. Matrix Factorization (SVD-based) — learn latent user/item factors from ratings
146. Content-Based Filtering — recommend items similar to what a user already liked
147. Neural Collaborative Filtering — learn user-item interactions with a neural network
148. Hybrid Recommender — combine collaborative + content-based signals

</details>

<details>
<summary><h2>8. Generalization / Avoiding Overfitting</h2></summary>

149. Train/Validation/Test Split — hold out data to measure real-world performance
150. Cross-Validation (K-Fold, Stratified, LOO) — validate robustly across multiple splits
151. Data Augmentation — synthetically expand training data variety
152. SMOTE / Under/Oversampling — rebalance classes to avoid biased learning
153. L1 Regularization (Lasso) — shrink and zero-out less useful feature weights
154. L2 Regularization (Ridge) — shrink weights smoothly to reduce overfitting
155. ElasticNet — combine L1 + L2 regularization
156. Pruning (Decision Trees) — cut back tree branches to reduce overfitting
157. Max Depth / Min Samples Leaf — constrain tree size to limit memorization
158. Dropout (generalization use) — randomly drop neurons to prevent co-adaptation
159. Batch Normalization (generalization use) — stabilizes training, mild regularizing effect
160. Early Stopping — stop training when validation performance stops improving
161. Weight Decay — penalize large weights during optimization
162. Label Smoothing — soften target labels to reduce overconfidence
163. Gradient Clipping — cap gradients to prevent unstable training
164. Noise Injection — add noise to inputs/weights to improve robustness
165. Bagging (generalization use) — reduce variance by averaging diverse models
166. Boosting (generalization caution) — reduces bias but needs early stopping to avoid overfitting
167. Learning Curves — plot train vs. validation loss to diagnose over/underfitting
168. Bias-Variance Tradeoff Analysis — balance underfitting vs. overfitting

</details>

---

## Unified Problem: "Build an Intelligent E-Commerce Platform"

One end-to-end problem, broken into sub-problems, showing which algorithm(s) solve each part and why.

| # | Sub-Problem | Algorithm Used | Why This Algorithm Solves It | Example |
|---|---|---|---|---|
| 1 | Understand raw sales/customer data before modeling | EDA (1–33): Histogram, Correlation, PCA, Outlier detection | Reveals data shape, relationships, and bad data before you build anything | Histogram shows order values are right-skewed; IQR method flags a $50,000 order as an outlier (likely a data entry error) |
| 2 | Segment customers into groups for targeted marketing | K-Means, Hierarchical Clustering, GMM (26–29) | Groups similar customers without needing labeled data | K-Means splits customers into "bargain hunters," "loyal high-spenders," "one-time buyers" based on purchase frequency/value |
| 3 | Predict which customers will churn (stop buying) | Logistic Regression, Random Forest, XGBoost (36, 40, 45) | Churn is a binary classification problem; ensembles handle mixed/noisy features well | XGBoost predicts a customer has 82% churn probability based on declining order frequency |
| 4 | Detect fraudulent transactions | Isolation Forest, LOF, Autoencoder (19, 20, 72) | Fraud is rare and different from normal patterns — anomaly detection fits better than classification | Autoencoder poorly reconstructs a transaction with an unusual amount/location combo, flagging it as fraud |
| 5 | Forecast next month's product demand | ARIMA, Prophet, LSTM (131, 133, 135) | Demand has trend + seasonality over time, which time-series models are built for | Prophet forecasts higher demand for winter jackets in November based on last 3 years' seasonal pattern |
| 6 | Recommend products to each shopper | Collaborative Filtering, Matrix Factorization, Neural CF (144–147) | Learns preference patterns from user-item interaction history | "Customers who bought running shoes also bought moisture-wicking socks" — collaborative filtering |
| 7 | Analyze product review sentiment | TF-IDF + Logistic Regression, or BERT (137, 68) | Text needs to be converted to features (TF-IDF) or understood contextually (BERT) before classifying sentiment | BERT classifies "the fabric feels cheap but shipping was fast" as mixed sentiment, not just positive/negative |
| 8 | Auto-tag and search product images | CNN Classifier, ViT (95, 96) | Learns visual features directly from pixels to classify image content | ResNet auto-tags an uploaded image as "red running shoe, size visible" for catalog search |
| 9 | Detect multiple products in a single warehouse camera frame | YOLO, Faster R-CNN (100, 99) | Needs to detect and localize multiple objects in one image, not just classify one | YOLO detects 5 different boxes on a conveyor belt in a single frame in real time |
| 10 | Segment defective regions on a returned product photo | U-Net, Mask R-CNN (105, 108) | Needs pixel-level (not just box-level) localization of the defect | U-Net highlights the exact torn region on a returned jacket photo |
| 11 | Power a customer-support chatbot | Transformer, GPT family (67, 69) | Needs to generate coherent, context-aware natural language responses | GPT-based bot answers "where's my order?" by reading order-status context and replying naturally |
| 12 | Optimize warehouse restocking decisions over time | Deep Q-Network (DQN), PPO (83, 86) | Restocking is a sequential decision problem where actions affect future rewards (cost vs. stockouts) | RL agent learns to reorder inventory just before stock hits zero, minimizing storage cost |
| 13 | Make sure churn/fraud models don't just memorize training data | Cross-Validation, Regularization (L1/L2), Dropout, Early Stopping (150, 153–164) | Ensures the model performs well on new, unseen customers — not just the training set | Model trained with dropout + early stopping keeps 91% accuracy on new customers instead of 99% on training but 60% on real data (overfitting) |
| 14 | Combine multiple models for a final churn decision | Stacking, Random Forest + XGBoost ensemble (40, 45, 48) | Different models catch different patterns; combining reduces error further than any single model | Meta-model blends Random Forest + XGBoost + Logistic Regression outputs for the final churn score |

This single system — customer data, sales history, fraud, product images, reviews, chatbot, warehouse camera, and restocking — touches essentially every category above, which is why real ML/AI systems at companies like Adobe/Salesforce combine several of these rather than using just one algorithm.
