"""
Module B Evaluation: Healthcare RAG Assistant & Retrieval Benchmark
Performs comparative experiments:
1. Vector Retrieval (ChromaDB + BGE-small) vs Vector Retrieval + BGE Cross-Encoder Re-Ranking
2. Query Normalization Impact (Raw queries vs Typo-corrected / expanded queries)
3. Retrieval metrics: Precision@1, Precision@3, Precision@5, Recall@1, Recall@3, Recall@5, MRR
4. Component latency breakdown: Normalizer, Embedding/Search, Re-Ranking, and Groq LLM Generation
"""

import os
import sys
import time
import json
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SERVER_DIR = os.path.join(BASE_DIR, "Server")
sys.path.insert(0, SERVER_DIR)

from vectordb.chroma_client import ChromaClient
from retrieval.normalizer import QueryNormalizer
from rag.answer_generator import AnswerGenerator
from fastembed.rerank.cross_encoder import TextCrossEncoder

def run_evaluation():
    print("=" * 70)
    print("Running Module B Evaluation: Healthcare RAG & Retrieval Benchmark")
    print("=" * 70)

    # 1. Initialize Components
    print("Loading ChromaDB vector client and embedding model...")
    chroma_client = ChromaClient()
    normalizer = QueryNormalizer()
    print("Loading BGE Cross-Encoder re-ranker...")
    reranker = TextCrossEncoder(model_name="BAAI/bge-reranker-base")

    # Initialize LLM for latency benchmark
    try:
        generator = AnswerGenerator()
        llm = generator.get_llm()
    except Exception as e:
        print(f"Warning: LLM could not be initialized: {e}")
        llm = None

    # 2. Benchmark Query Suite (20 clinical and service queries with ground truth intent keywords)
    benchmark_queries = [
        # (query_id, raw_query, normalized_target_keywords, category)
        ("Q01", "What is the price of VITAMIN D TOTAL?", ["vitamin d", "mrp", "1800", "im0283", "total"], "Pricing"),
        ("Q02", "What about B12 test cost?", ["vitamin b12", "b12", "cost", "mrp"], "Pricing"),
        ("Q03", "cost of cbc blood test", ["cbc", "complete blood count", "haematology"], "Acronym"),
        ("Q04", "how much is lft test", ["lft", "liver function", "bilirubin", "sgpt", "sgot"], "Acronym"),
        ("Q05", "kft panel price and parameters", ["kft", "kidney function", "renal", "creatinine", "bun"], "Acronym"),
        ("Q06", "sugar test cost", ["glucose", "blood sugar", "fasting", "postprandial"], "Layperson"),
        ("Q07", "colestrol test price", ["cholesterol", "lipid", "triglycerides", "hdl", "ldl"], "Typo"),
        ("Q08", "thyrod test rate", ["thyroid", "tsh", "t3", "t4"], "Typo"),
        ("Q09", "hba1c test price", ["hba1c", "glycosylated hemoglobin", "diabetes"], "Acronym"),
        ("Q10", "creatanine serum test", ["creatinine", "kidney", "renal"], "Typo"),
        ("Q11", "centres in Andhra Pradesh", ["andhra pradesh", "centre", "visakhapatnam", "vijayawada"], "Location"),
        ("Q12", "centres in Maharashtra", ["maharashtra", "mumbai", "pune", "thane", "centre"], "Location"),
        ("Q13", "diagnostic lab in Kalyan", ["kalyan", "centre", "address"], "Location"),
        ("Q14", "centres in Goa", ["goa", "panaji", "margao", "centre"], "Location"),
        ("Q15", "full body health checkup package", ["full body", "package", "health checkup"], "Layperson"),
        ("Q16", "crp test cost", ["crp", "c-reactive protein", "serology"], "Acronym"),
        ("Q17", "platelet count test", ["platelet", "cbc", "complete blood count"], "Layperson"),
        ("Q18", "dengue test details and price", ["dengue", "ns1", "antigen", "igm", "igg"], "Layperson"),
        ("Q19", "electrolite serum test cost", ["electrolyte", "sodium", "potassium", "chloride"], "Typo"),
        ("Q20", "fasting requirement for blood sugar", ["fasting", "blood sugar", "sample", "glucose"], "Preparation")
    ]

    results = {}

    # Metrics containers
    # Dense retrieval alone (top 1, 3, 5)
    prec_dense = {1: [], 3: [], 5: []}
    rec_dense = {1: [], 3: [], 5: []}
    mrr_dense = []

    # Dense + Cross-Encoder Reranked (top 1, 3, 5)
    prec_rerank = {1: [], 3: [], 5: []}
    rec_rerank = {1: [], 3: [], 5: []}
    mrr_rerank = []

    # Query Normalization Ablation: Raw vs Normalized
    norm_improvement = []

    # Latency tracking (in milliseconds)
    latencies = {
        "normalization": [],
        "vector_search": [],
        "reranking": [],
        "llm_generation": []
    }

    base_retriever = chroma_client.as_retriever(search_type="similarity", search_kwargs={"k": 15})

    def is_chunk_relevant(doc_text, target_keywords):
        lower_text = doc_text.lower()
        # Document is relevant if it matches at least one primary target keyword
        return any(kw in lower_text for kw in target_keywords)

    print(f"Evaluating {len(benchmark_queries)} benchmark queries across retrieval configurations...")

    for qid, raw_q, targets, cat in benchmark_queries:
        # Step 1: Query Normalization
        t0 = time.perf_counter()
        normalized_q = normalizer.normalize(raw_q)
        t_norm = (time.perf_counter() - t0) * 1000
        latencies["normalization"].append(t_norm)

        # Step 2: Dense Vector Retrieval (k=15 for reranker candidate pool)
        t1 = time.perf_counter()
        retrieved_docs = base_retriever.invoke(normalized_q)
        t_dense = (time.perf_counter() - t1) * 1000
        latencies["vector_search"].append(t_dense)

        # Raw query retrieval (for normalization ablation comparison)
        raw_docs = base_retriever.invoke(raw_q)
        raw_rel_top3 = sum(1 for d in raw_docs[:3] if is_chunk_relevant(d.page_content, targets))
        norm_rel_top3 = sum(1 for d in retrieved_docs[:3] if is_chunk_relevant(d.page_content, targets))
        norm_improvement.append({
            "query_id": qid,
            "raw_query": raw_q,
            "normalized_query": normalized_q,
            "raw_top3_relevant": raw_rel_top3,
            "norm_top3_relevant": norm_rel_top3
        })

        # Calculate metrics for Dense Vector Search (Baseline)
        dense_top5 = retrieved_docs[:5]
        dense_relevance = [1 if is_chunk_relevant(d.page_content, targets) else 0 for d in dense_top5]

        for k in [1, 3, 5]:
            hits = sum(dense_relevance[:k])
            prec_dense[k].append(hits / k)
            # Estimate recall against target occurrence
            rec_dense[k].append(min(hits / 1.0, 1.0))

        # MRR Dense
        rank_d = 0
        for idx, rel in enumerate(dense_relevance):
            if rel == 1:
                rank_d = idx + 1
                break
        mrr_dense.append(1.0 / rank_d if rank_d > 0 else 0.0)

        # Step 3: Cross-Encoder Re-Ranking
        doc_texts = [d.page_content for d in retrieved_docs]
        t2 = time.perf_counter()
        # Rerank with FastEmbed cross encoder
        scores = list(reranker.rerank(normalized_q, doc_texts))
        t_rerank = (time.perf_counter() - t2) * 1000
        latencies["reranking"].append(t_rerank)

        # Sort documents by cross-encoder score descending
        # FastEmbed reranker yields either floats or dicts with 'score' / 'index'
        if len(scores) > 0 and hasattr(scores[0], 'score'):
            scored_pairs = sorted(zip(scores, retrieved_docs), key=lambda x: x[0].score, reverse=True)
            reranked_docs = [pair[1] for pair in scored_pairs][:5]
        elif len(scores) > 0 and isinstance(scores[0], dict) and "score" in scores[0]:
            scored_pairs = sorted(zip(scores, retrieved_docs), key=lambda x: x[0]["score"], reverse=True)
            reranked_docs = [pair[1] for pair in scored_pairs][:5]
        else:
            scored_pairs = sorted(zip(scores, retrieved_docs), key=lambda x: x[0], reverse=True)
            reranked_docs = [pair[1] for pair in scored_pairs][:5]

        rerank_relevance = [1 if is_chunk_relevant(d.page_content, targets) else 0 for d in reranked_docs]

        for k in [1, 3, 5]:
            hits = sum(rerank_relevance[:k])
            prec_rerank[k].append(hits / k)
            rec_rerank[k].append(min(hits / 1.0, 1.0))

        # MRR Rerank
        rank_r = 0
        for idx, rel in enumerate(rerank_relevance):
            if rel == 1:
                rank_r = idx + 1
                break
        mrr_rerank.append(1.0 / rank_r if rank_r > 0 else 0.0)

    # Step 4: Measure LLM Generation Latency on sample queries
    if llm:
        print("Measuring Groq API generation latency...")
        sample_prompts = [
            "What is the price of Vitamin D total?",
            "Do I need to fast for lipid profile?",
            "List your diagnostic centres in Maharashtra."
        ]
        for p in sample_prompts:
            t3 = time.perf_counter()
            try:
                _ = llm.invoke(p)
                t_llm = (time.perf_counter() - t3) * 1000
                latencies["llm_generation"].append(t_llm)
            except Exception as e:
                print(f"LLM sample call failed: {e}")

    # Compile Summary
    summary_dense = {
        "Precision@1": round(float(np.mean(prec_dense[1])), 4),
        "Precision@3": round(float(np.mean(prec_dense[3])), 4),
        "Precision@5": round(float(np.mean(prec_dense[5])), 4),
        "Recall@1": round(float(np.mean(rec_dense[1])), 4),
        "Recall@3": round(float(np.mean(rec_dense[3])), 4),
        "Recall@5": round(float(np.mean(rec_dense[5])), 4),
        "MRR": round(float(np.mean(mrr_dense)), 4)
    }

    summary_rerank = {
        "Precision@1": round(float(np.mean(prec_rerank[1])), 4),
        "Precision@3": round(float(np.mean(prec_rerank[3])), 4),
        "Precision@5": round(float(np.mean(prec_rerank[5])), 4),
        "Recall@1": round(float(np.mean(rec_rerank[1])), 4),
        "Recall@3": round(float(np.mean(rec_rerank[3])), 4),
        "Recall@5": round(float(np.mean(rec_rerank[5])), 4),
        "MRR": round(float(np.mean(mrr_rerank)), 4)
    }

    latency_summary = {
        "mean_normalization_ms": round(float(np.mean(latencies["normalization"])), 2),
        "mean_vector_search_ms": round(float(np.mean(latencies["vector_search"])), 2),
        "mean_cross_encoder_rerank_ms": round(float(np.mean(latencies["reranking"])), 2),
        "mean_llm_generation_ms": round(float(np.mean(latencies["llm_generation"])), 2) if latencies["llm_generation"] else 0.0,
        "mean_total_pipeline_ms": round(
            float(np.mean(latencies["normalization"]) + np.mean(latencies["vector_search"]) + (np.mean(latencies["llm_generation"]) if latencies["llm_generation"] else 0.0)),
            2
        )
    }

    results["dense_vector_retrieval_baseline"] = summary_dense
    results["vector_plus_cross_encoder_rerank"] = summary_rerank
    results["query_normalization_ablation"] = norm_improvement
    results["latency_breakdown_ms"] = latency_summary

    print("\n--- Comparative Retrieval Results ---")
    print(f"Dense Vector Retrieval alone: P@1={summary_dense['Precision@1']}, P@3={summary_dense['Precision@3']}, MRR={summary_dense['MRR']}")
    print(f"Dense Vector + Cross-Encoder:  P@1={summary_rerank['Precision@1']}, P@3={summary_rerank['Precision@3']}, MRR={summary_rerank['MRR']}")
    print(f"Latency Profile: Norm={latency_summary['mean_normalization_ms']}ms, Vector={latency_summary['mean_vector_search_ms']}ms, ReRank={latency_summary['mean_cross_encoder_rerank_ms']}ms, LLM={latency_summary['mean_llm_generation_ms']}ms")

    out_file = os.path.join(os.path.dirname(__file__), "results_retrieval.json")
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Saved Module B results to {out_file}")
    return results

if __name__ == "__main__":
    run_evaluation()
