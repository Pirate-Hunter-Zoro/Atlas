<!--
Section 9 of 10 of manuscript.md, split out by the
Paper-Writer pipeline. DERIVED FILE: the assembled document is the
source of truth and this is produced from it, so an edit made here is
lost the next time the paper is built. Edit manuscript.md.

Section heading: References
-->

# References

<!--
References are numbered by order of first appearance in the text, counting
the abstract, and the numbering is CONTIGUOUS FROM 1 with every entry cited.
Vancouver style, first six authors then "et al." Bibliographic details
verified against PubMed / ACL Anthology / publisher records.

RENUMBERED THREE TIMES. Read this block before quoting a reference number out
of review/ or reserve/, because those documents record the numbers that were
in force when they were written and no attempt was made to rewrite history
there.

Passes one and two, both 2026-09-06, were REMOVALS. The previous ref 24
(Lee C et al, "How to correctly report LLM-as-a-judge evaluations") existed
only to pre-empt an objection to the similarity-judge weighting arm; the arm's
RESULTS left the main text and the reference left with them, so previous 25-31
became 24-30. Then the arm stopped being MENTIONED at all, because a paper
that describes an analysis and then declines to report it advertises work the
reader cannot check. Ref 15 (Sellergren et al, MedGemma technical report) was
cited only from those two sentences and left with them, so 16-31 became 15-30.
Both the judge results and their citation are complete in
reserve/llm_similarity_judge.md, which carries its own inline citations and no
numbered list.

Pass three, 2026-09-07, was the ORDER. The list had never actually been in
order of first appearance -- the Introduction cited [23-25] before [4] -- and
this block claimed it was. Every marker was remapped and the list reordered.
The map, old to new:

     1 ->  1     2 ->  4     3 ->  5     4 -> 18     5 -> 19     6 -> 20
     7 -> 21     8 -> 30     9 -> 15    10 ->  3    11 -> 28    12 -> 23
    13 -> 24    14 -> 25    15 -> 26    16 -> 27    17 -> 16    18 -> 17
    19 ->  2    20 -> 13    21 -> 14    22 -> 22    23 ->  6    24 ->  7
    25 ->  8    26 ->  9    27 -> 10    28 -> 11    29 -> 12    30 -> 29

Two markers stopped being single ranges because the pass broke their runs:
[4-8] is now [18-21,30] and [25,27-29] is now [8,10-12]. Both are correct
Vancouver. Ref 30 (Chekroud 2021) carries the last number because the group in
Discussion, *Comparison with prior work*, is the only place it is ever cited.
The same remap was applied to supplement.md and tripod_ai_checklist.md.

Refs 6-12 (Cepeda, Fabbri, Iveson, Liberman, Lage, Lee DY, Walsh) were added
2026-09-03 from the senior author's review, and were 24-30 before pass three.
VERIFIED against PubMed records and, where obtainable, the papers themselves.
Three had wrong fields as first entered and are corrected here (Cepeda's issue
and pages; Iveson's author list and volume/pages; Walsh's author list). EVERY
DISCRIMINATION FIGURE QUOTED FROM THEM IN THE DISCUSSION IS CONFIRMED:
Liberman AUC 0.83 over a 24-month follow-up in 35,246 eligible people; Lage
0.652 (95% CI 0.623-0.682) in the second health system with top-quintile lift
1.99; Lee DY 0.684 structured-only, 0.569 notes-only, 0.728 combined, 0.794
with MRI as the highest; Walsh 0.58-0.64 internal falling to 0.51-0.58
external. Five of the seven are held as PDFs; Lage and Lee DY are not open
access and have reprint requests drafted.

Ref 11 is Lee DY (multimodal TRD prediction), and it was ref 28 before pass
three and ref 29 before that. The removed LLM-as-a-judge reference was also a
"Lee". There is no longer any other Lee in the list.
-->

1. Al-Harbi KS. Treatment-resistant depression: therapeutic trends,
   challenges, and future directions. Patient Prefer Adherence.
   2012;6:369-388. doi:10.2147/PPA.S29716.

2. Forthman KL, Kuplicki R, Thompson WK, Nemeroff CB, Si Y, Fan CC, et al.
   Treatment resistant depression: socio-demographic characteristics,
   comorbidity and treatment patterns from the All of Us Research Program.
   J Affect Disord. 2025;390:119858. doi:10.1016/j.jad.2025.119858.

3. Collins GS, Moons KGM, Dhiman P, Riley RD, Beam AL, Van Calster B,
   et al. TRIPOD+AI statement: updated guidance for reporting clinical
   prediction models that use regression or machine learning methods. BMJ.
   2024;385:e078378. doi:10.1136/bmj-2023-078378.

4. Gaynes BN, Lux L, Gartlehner G, Asher G, Forman-Hoffman V, Green J,
   et al. Defining treatment-resistant depression. Depress Anxiety.
   2020;37(2):134-145. doi:10.1002/da.22968.

5. Rush AJ, Trivedi MH, Wisniewski SR, Nierenberg AA, Stewart JW, Warden
   D, et al. Acute and longer-term outcomes in depressed outpatients
   requiring one or several treatment steps: a STAR\*D report. Am J
   Psychiatry. 2006;163(11):1905-1917. doi:10.1176/ajp.2006.163.11.1905.

6. Cepeda MS, Reps J, Fife D, Blacketer C, Stang P, Ryan P. Finding
   treatment-resistant depression in real-world data: how a data-driven
   approach compares with expert-based heuristics. Depress Anxiety.
   2018;35(3):220-228. doi:10.1002/da.22705.

7. Fabbri C, Hagenaars SP, John C, Williams AT, Shrine N, Moles L, et al.
   Genetic and clinical characteristics of treatment-resistant depression
   using primary care records in two UK cohorts. Mol Psychiatry.
   2021;26(7):3363-3373. doi:10.1038/s41380-021-01062-9.

8. Iveson MH, Ball EL, Lo CWH, Falis M, Lewis CM, Whalley HC. Treatment
   resistant depression in electronic health records: definitions matter.
   BMC Psychiatry. 2026;26(1):453. doi:10.1186/s12888-026-08085-y.

9. Liberman JN, Davis T, Pesa J, Chow W, Verbanac J, Heverly-Fitt S,
   et al. Predicting incident treatment-resistant depression: a model
   designed for health systems of care. J Manag Care Spec Pharm.
   2020;26(8):987-995. doi:10.18553/jmcp.2020.26.8.987.

10. Lage I, McCoy TH, Perlis RH, Doshi-Velez F. Efficiently identifying
    individuals at high risk for treatment resistance in major depressive
    disorder using electronic health records. J Affect Disord.
    2022;306:254-259. doi:10.1016/j.jad.2022.02.046.

11. Lee DY, Kim N, Park C, Gan S, Son SJ, Park RW, et al. Explainable
    multimodal prediction of treatment-resistance in patients with
    depression leveraging brain morphometry and natural language
    processing. Psychiatry Res. 2024;334:115817.
    doi:10.1016/j.psychres.2024.115817.

12. Walsh CG, Ripperger M, McCoy TH, Castro V, Hu Y, Kirchner HL, et al.
    Generalizability of risk models for treatment-resistant depression
    across three health systems. medRxiv. 2025. Preprint.
    doi:10.1101/2025.05.21.25328089.

13. Shmatko A, Jung AW, Gaurav K, Brunak S, Mortensen LH, Birney E, et al.
    Learning the natural history of human disease with generative
    transformers. Nature. 2025;647(8082):248-256.
    doi:10.1038/s41586-025-09529-3.

14. Waxler S, Blazek P, White D, Sneider D, Chung K, Nagarathnam M, et al.
    Generative medical event models improve with scale. arXiv.
    2025;arXiv:2508.12104. doi:10.48550/arXiv.2508.12104.

15. Hegselmann S, von Arnim G, Rheude T, Kronenberg N, Sontag D, Hindricks
    G, et al. Large language models are powerful electronic health record
    encoders. arXiv:2502.17403. 2025.

16. González HM, Vega WA, Williams DR, Tarraf W, West BT, Neighbors HW.
    Depression care in the United States: too little for too few. Arch Gen
    Psychiatry. 2010;67(1):37-46. doi:10.1001/archgenpsychiatry.2009.168.

17. Alegría M, Chatterji P, Wells K, Cao Z, Chen CN, Takeuchi D, et al.
    Disparity in depression treatment among racial and ethnic minority
    populations in the United States. Psychiatr Serv.
    2008;59(11):1264-1272. doi:10.1176/ps.2008.59.11.1264.

18. Perlis RH. A clinical risk stratification tool for predicting
    treatment resistance in major depressive disorder. Biol Psychiatry.
    2013;74(1):7-14. doi:10.1016/j.biopsych.2012.12.007.

19. Kautzky A, Baldinger-Melich P, Kranz GS, Vanicek T, Souery D,
    Montgomery S, et al. A new prediction model for evaluating
    treatment-resistant depression. J Clin Psychiatry. 2017;78(2):215-222.
    doi:10.4088/JCP.15m10381.

20. Sheu YH, Magdamo C, Miller M, Das S, Blacker D, Smoller JW.
    AI-assisted prediction of differential response to antidepressant
    classes using electronic health records. npj Digit Med. 2023;6:73.
    doi:10.1038/s41746-023-00817-8.

21. Chekroud AM, Zotti RJ, Shehzad Z, Gueorguieva R, Johnson MK, Trivedi
    MH, et al. Cross-trial prediction of treatment outcome in depression:
    a machine learning approach. Lancet Psychiatry. 2016;3(3):243-250.
    doi:10.1016/S2215-0366(15)00471-X.

22. Hegselmann S, Shen SZ, Gierse F, Agrawal M, Sontag D, Jiang X. A
    data-centric approach to generate faithful and high quality patient
    summaries with large language models. Proc Mach Learn Res.
    2024;248:339-379.

23. Xiao S, Liu Z, Zhang P, Muennighoff N, Lian D, Nie JY. C-Pack: packed
    resources for general Chinese embeddings. In: Proceedings of the 47th
    International ACM SIGIR Conference on Research and Development in
    Information Retrieval (SIGIR '24); 2024 Jul 14-18; Washington (DC).
    New York: ACM; 2024. p. 641-649. doi:10.1145/3626772.3657878.

24. Li C, Qin M, Xiao S, Chen J, Luo K, Shao Y, et al. Making text
    embedders few-shot learners. arXiv:2409.15700. 2024.

25. Zhang Y, Li M, Long D, Zhang X, Lin H, Yang B, et al. Qwen3 embedding:
    advancing text embedding and reranking through foundation models.
    arXiv:2506.05176. 2025.

26. Pedregosa F, Varoquaux G, Gramfort A, Michel V, Thirion B, Grisel O,
    et al. Scikit-learn: machine learning in Python. J Mach Learn Res.
    2011;12:2825-2830.

27. Chen T, Guestrin C. XGBoost: a scalable tree boosting system. In:
    Proceedings of the 22nd ACM SIGKDD International Conference on
    Knowledge Discovery and Data Mining (KDD '16); 2016 Aug 13-17; San
    Francisco (CA). New York: ACM; 2016. p. 785-794.
    doi:10.1145/2939672.2939785.

28. Reimers N, Gurevych I. Sentence-BERT: sentence embeddings using
    Siamese BERT-networks. In: Proceedings of the 2019 Conference on
    Empirical Methods in Natural Language Processing and the 9th
    International Joint Conference on Natural Language Processing
    (EMNLP-IJCNLP); 2019 Nov; Hong Kong. Stroudsburg (PA): Association for
    Computational Linguistics; 2019. p. 3982-3992.
    doi:10.18653/v1/D19-1410.

29. Ferguson M. TRD-EHR: analysis code for treatment-resistant depression
    prediction from electronic health records. GitHub. 2026. URL:
    https://github.com/Pirate-Hunter-Zoro/TRD-EHR [accessed 2026-09-06]

30. Chekroud AM, Bondar J, Delgadillo J, Doherty G, Wasil A, Fokkema M,
    et al. The promise of machine learning in predicting treatment
    outcomes in psychiatry. World Psychiatry. 2021;20(2):154-170.
    doi:10.1002/wps.20882.
