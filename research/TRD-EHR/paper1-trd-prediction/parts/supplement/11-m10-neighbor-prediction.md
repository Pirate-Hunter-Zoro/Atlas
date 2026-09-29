<!--
Section 11 of 27 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: M10 Neighbor Prediction
-->

# M10 Neighbor Prediction

For EMBEDDED only, the predicted TRD probability for query patient q was the similarity-weighted mean of binary TRD labels among its k retrieved training neighbors:

$$\widehat{P}(TRD \mid q) = \frac{\sum_{i = 1}^{k}w_{i}\, y_{i}}{\sum_{i = 1}^{k}w_{i}}, \qquad w_{i} = \max\{s_{i}, 0\}^{\alpha},$$

where $y_{i} \in \{ 0,1\}$ is neighbor $i$'s TRD label, $s_{i}$ its similarity to q, and $\alpha$ a sharpening exponent. Neighborhood concentration was summarized by the effective sample size,

$$ESS = \frac{\left( \sum_{i = 1}^{k}w_{i} \right)^{2}}{\sum_{i = 1}^{k}w_{i}^{2}},$$

which equals $k$ when all weights are equal and falls as weight concentrates on fewer neighbors.

Two similarity metrics were compared. Plain cosine similarity used the raw embeddings. Importance-weighted cosine similarity standardized each dimension with the embedded logistic regression's own scaler, $z_{d} = (x_{d} - \mu_{d})/\sigma_{d}$, and weighted dimension $d$ by its share of that model's absolute coefficients:

$$\mathrm{sim}_{w}(x,y) = \frac{\sum_{d}w_{d}\, z_{d}(x)\, z_{d}(y)}{\sqrt{\sum_{d}w_{d}\, z_{d}(x)^{2}}\,\sqrt{\sum_{d}w_{d}\, z_{d}(y)^{2}}}, \qquad w_{d} = \frac{|\beta_{d}|}{\sum_{e}|\beta_{e}|}.$$

The coefficients came from the model fitted on training patients, so no test outcome entered a risk score. The metric is supervised, whereas plain cosine similarity is not. Of 4,096 dimensions, 385 had non-zero coefficients, and the top 41 (1%) carried 31% of the absolute coefficient mass.

The primary analysis used plain cosine similarity with k = 50 and $\alpha$ = 5. A sweep evaluated every k from 1 to all 34,063 training patients for both metrics, under $\alpha$ = 1, 2, and 5. Nearest retrieval selected the k most similar training patients. Farthest retrieval, which selected the least similar, and random retrieval served as negative controls at k = 50. These analyses were restricted to embeddings; no mixed-data similarity metric was specified for FEATURE.
