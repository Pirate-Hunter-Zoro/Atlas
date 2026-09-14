<!--
Section 10 of 22 of supplement.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit supplement.md.

Section heading: Supplement M10. Neighbor-weighted retrieval prediction
-->

# Supplement M10. Neighbor-weighted retrieval prediction

For EMBEDDED only, the predicted TRD probability for query patient q was the
weighted mean of binary TRD labels among K = 50 retrieved training neighbors:

$$\hat{P}(\mathrm{TRD} \mid q) = \frac{\sum_{i=1}^{K} w_i\, y_i}{\sum_{i=1}^{K} w_i},$$

where $y_i \in \{0,1\}$ is neighbor $i$'s TRD label and $w_i$ its non-negative
weight. No model is fitted anywhere in this arm. The predictor is the observed
outcome rate of a retrieved set of real patients. That is what makes it a
direct test of the premise that a patient's course can be read from the
courses of their closest analogues.

Two weighting strategies are reported. Under uniform weighting all weights are
equal and the prediction is the raw TRD rate of the retrieved set. Under
cosine weighting each neighbor is weighted by its cosine similarity to the
anchor.
Neighborhood concentration was summarized by the effective sample size,

$$\mathrm{ESS} = \frac{\left(\sum_{i=1}^{K} w_i\right)^2}{\sum_{i=1}^{K} w_i^2},$$

which equals $K$ under uniform weighting and falls as weight concentrates on
fewer neighbors. Cosine weighting leaves it essentially unchanged, at a mean ESS of 49.98
against 50.00 under nearest retrieval. That is the mechanical reason the two
weightings return nearly identical discrimination. Within a nearest-neighbor
set the similarities are all high and all close together, so the weights are
nearly uniform whatever the formula.

Two retrieval schemes were evaluated. *Nearest* selects the K training
patients of highest cosine similarity. *Random* draws K training
patients uniformly, as a negative control. This arm is embedding-only,
because cosine similarity is not well defined over mixed categorical and
numeric features.

All test identifiers were removed from the searchable index. Each test patient
was a query anchor, and every neighbor and neighbor outcome came from the
training set, which prevents self-retrieval, test-to-test outcome propagation,
and any direct use of a test label in prediction.
