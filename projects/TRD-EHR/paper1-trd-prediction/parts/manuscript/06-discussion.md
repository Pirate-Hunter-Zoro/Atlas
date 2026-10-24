<!--
Section 6 of 15 of manuscript.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit manuscript.md.

Section heading: Discussion
-->

# Discussion

## Principal Findings

We asked whether pretrained narrative embeddings improve prediction of a treatment-switching proxy for TRD beyond structured feature vectors. In this cohort, they did not demonstrate superior discrimination over the strongest feature-vector model. The leading models achieved ROC AUCs of 0.657 (95% CI 0.643--0.672) and 0.649 (95% CI 0.634--0.664), with a paired difference of 0.008 (95% CI −0.003 to 0.019). This finding supports structured features as a practical benchmark; it does not establish equivalence or isolate the effect of encoding identical information.

The choice of classifier changed the result. Embeddings improved logistic regression but reduced discrimination for each tree ensemble, and logistic regression led the embedded models across all encoders. This pattern is consistent with regularized linear models accommodating distributed embedding information more effectively under the tested settings. Differences in dimensionality, regularization, and tuning may also contribute. The analysis supports evaluating the representation and classifier together, without attributing the pattern to an intrinsic property of clinical information.

The predictive signal was concentrated in familiar aspects of clinical history. Psychiatric comorbidity, medication burden, and prior treatment contributed most to embedded discrimination, while feature-vector models highlighted related markers of illness complexity. Nearest-neighbor analyses showed that embedding proximity was associated with the outcome: randomly chosen neighbors gave chance discrimination at every neighborhood size. Retrieval still fell short of the trained classifiers at every neighborhood size, and the number of neighbors mattered more than how similarity was weighted. Taken together, these findings suggest that embeddings reorganized useful information already recorded in the EHR; they do not demonstrate a new measure of treatment resistance.

## Comparison With Prior Work

Our discrimination estimates fall within the range reported for structured EHR models, but differences in outcome definition and validation preclude direct performance rankings. Liberman and colleagues reported an internally evaluated ROC AUC of 0.83 over 24 months \[12\], whereas Lage and colleagues reported an externally validated ROC AUC of 0.652 \[13\]. A smaller multimodal study achieved 0.684 with structured EHR data and 0.728 after adding clinical notes \[15\]. In a 3-system study, internal ROC AUCs of 0.58--0.64 declined to 0.51--0.58 under external validation \[14\].

The present contribution is the direct comparison of practical representation pipelines under a shared cohort, prediction time, and test split. It does not set a performance ceiling for EHR prediction. Adding independently informative measurements may improve prediction, as may better outcome ascertainment. Re-encoding existing records should therefore be judged by incremental performance, reproducibility, and implementation burden rather than model size alone.

## Clinical Interpretation and Limitations

The main limitation is the target. Repeated antidepressant switching can reflect inadequate response, but also tolerability, preference, clinician behavior, and access. The study did not verify failed adequate trials or symptom trajectories, and the index prescription was not necessarily a patient's first antidepressant exposure. The results therefore need to be seen as focused on subsequent treatment switching in patients with recorded depression, not necessarily confirmed incident TRD. Future investigations with access to unstructured elements of the EHR record may need to examine more variation across EHR definitions since they may have considerable effects on what the label represents \[9-11\].

There are several noteworthy limitations. Both representations were built from the same predictors, selected by hand before either pipeline existed, and the narratives are a fixed template over that selection. The comparison is therefore between two encodings of curated fields. It does not show what an encoder would do with an unselected record. Temporal separation of predictors and outcome reduces direct leakage from future treatment history. However, it does not necessarily remove selection or observation bias. Eligibility required subsequent follow-up, the source extract excluded patients recorded as deceased at extraction, and care outside the system could be missed. The single-system, depression-enriched sample and random internal validation also limit transportability and the interpretation of absolute risk. The number of neighbors for retrieval was chosen on the test patients, so the best retrieval values are optimistic; this makes the gap to the trained classifiers, if anything, larger.

The minimal change after race/ethnicity or social-determinant permutation is useful but does not establish fairness. These fields may be incompletely recorded, related information may remain in other predictors, and the outcome depends on access to treatment \[28,29\]. The subgroup analyses were limited by small event counts and broad racial aggregation, with unresolved differences in discrimination and calibration. Similarly, concept permutation measures sensitivity to altered inputs rather than a causal contribution; correlated fields and implausible combinations after permutation limit attribution.


## Interpreting Nearest-Neighbor Retrieval

Retrieval shows that the embeddings place patients with similar outcomes near each other. Randomly chosen neighbors gave chance discrimination, and nearest neighbors rose well above it for every encoder. A trained logistic regression on the same embedding still did better at every neighborhood size.

The number of neighbors works like a smoothing setting. With 1 neighbor, a patient's risk is another patient's 0 or 1 outcome, which is mostly noise. Averaging more neighbors steadies the estimate. That is why both nearest-neighbor curves rose from near chance at k = 1 for every encoder. Past a few hundred neighbors, the added patients are less alike in outcome risk, and plain cosine retrieval drifted down. The best k is therefore not a count of patient types or risk factors. It need not match the number of embedding dimensions a model relies on, and in these 4 encoders it did not.

Weighting by logistic-regression coefficients changes which patients count as close. Plain cosine similarity reflects everything in the narrative, including content unrelated to the outcome. The weighted metric emphasizes the dimensions the classifier found predictive. Learning a distance from the outcome is an established way to improve nearest-neighbor prediction \[30\]. It also means the weighted metric borrows from a supervised model, so its gains are not a property of the pretrained encoder alone.

Weighted retrieval still trails the logistic regression, and one reason is built into the weights. They keep the size of each coefficient but drop its sign. The classifier instead adds signed contributions into one score, so 2 patients can reach the same predicted risk through different features. Those 2 patients need not be close under the weighted similarity.

Two cautions limit these interpretations. First, best k and the maxima were chosen on the test patients, and choosing a setting in the same patients it is scored on overstates performance \[31\]. A fair test would fit the weights and choose k inside the training data, for example by nested cross-validation, then score held-out patients once. Second, similar records are not similar biology. Neighbors share recorded psychiatric history, medication burden, prior treatment, and patterns of care. Retrieval does not identify TRD subtypes, and it cannot separate failed treatment from switching for tolerability, access, or prescribing habits. Likewise, the lower results for bge-small-en-v1.5 do not show that fewer dimensions caused them, because the encoders also differ in architecture and training.

## Implications and Next Steps

The current findings are useful, but the results do not support clinical deployment. The next steps are to validate the switching phenotype against treatment histories and symptom change, then evaluate frozen pipelines in temporal and external cohorts. Evaluation should compare embeddings with compact psychiatric-history, medication, and utilization baselines and report precision--recall performance, individual-level calibration, subgroup errors, and decision-analytic net benefit at prespecified thresholds. However, for an embedding pipeline to justify its added complexity, it should improve prediction, transportability, or clinical workflow beyond a simpler model. It is also possible that a more clinically informative prediction target may be as impactful for future investigations as a more elaborate representation of the case embedding.

## Conclusions

At the index antidepressant prescription, structured feature vectors and narrative embeddings provided modest discrimination for a subsequent treatment-switching proxy for TRD, without demonstrated superiority of the strongest embedded model. Performance depended on the classifier. Progress toward clinical use requires better validation of the outcome and evidence that prediction improves decisions across patients and health systems.
