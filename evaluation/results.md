# Metsandusotsingu hindamistulemus

- Andmestik: `kaur-forest-search-et-v2` (külmutatud 2026-08-16)
- SHA-256: `6408f0b29aabbcecb153bd75fe39001e4c32793ae5a59d71a30b5a006be76d79`
- Mootor: `prototype-bm25-estonian-char3-terminology-rrf-rerank-v2`
- Värav: **LÄBITUD**
- Staatus: prototype; KAUR content-owner approval pending

| Jaotus | Päringuid | Meetod | Recall@3 | nDCG@3 | MRR |
|---|---:|---|---:|---:|---:|
| development | 72 | baseline | 0.7917 | 0.7452 | 0.7493 |
| development | 72 | hybrid | 0.9722 | 0.9396 | 0.9345 |
| locked | 30 | baseline | 0.7667 | 0.6762 | 0.6639 |
| locked | 30 | hybrid | 1.0000 | 0.9139 | 0.8833 |

Lukustatud jaotuse Recall@3 absoluutne paranemine: `+0.2333`.
Lukustatud jaotuse extractive-vastuse allikaväljade täpne faithfulness: `1.0000`.

## Väravakontrollid

- ✓ `hybrid_recall_at_3_gte_0_90`
- ✓ `recall_gain_gte_0_15`
- ✓ `hybrid_ndcg_at_3_gte_0_80`
- ✓ `no_critical_retrieval_regression`
- ✓ `citation_integrity_100_percent`
- ✓ `extractive_answer_faithfulness_100_percent`
- ✓ `redirect_and_abstention_100_percent`
- ✓ `all_required_topics_covered`

## Lukustatud jaotuse retrieval'i möödalasud

Puuduvad.

Kontrollkogum on prototüübi tõend, mitte KAURi sisuline heakskiit. Enne pilooti kinnitab KAUR kuldmärgendid ja lävendid ning avaldab uue versiooniga lukustatud kogumi.
