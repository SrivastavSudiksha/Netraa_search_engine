import time
import json
import statistics
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from query.processor import QueryProcessor

TEST_QUERIES = [
    "python programming",
    "artificial intelligence",
    "machine learning",
    "cricket world cup",
    "film making",
    "deep learning neural networks",
    "food cooking recipes",
    "football premier league",
    "health fitness",
    "technology news",
    "natural language processing",
    "robotics automation",
    "climate environment",
    "history ancient",
    "science discovery",
]

def run_benchmark(n_runs=3):
    print("Loading index...")
    qp = QueryProcessor()
    qp.load()
    print(f"Index loaded — {len(qp.index)} terms, {len(qp.doc_store)} docs\n")

    all_latencies = []
    query_stats = []

    print(f"{'Query':<35} {'Hits':>4}  {'Avg':>7}  {'Min':>7}  {'Max':>7}")
    print("-" * 70)

    for query in TEST_QUERIES:
        latencies = []
        hits = 0
        for _ in range(n_runs):
            t0 = time.perf_counter()
            results = qp.search(query, top_k=10)
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000)
            hits = len(results)

        avg = statistics.mean(latencies)
        mn  = min(latencies)
        mx  = max(latencies)
        all_latencies.extend(latencies)
        query_stats.append({"query": query, "hits": hits, "avg_ms": round(avg, 2)})
        print(f"{query:<35} {hits:>4}  {avg:>6.1f}ms  {mn:>6.1f}ms  {mx:>6.1f}ms")

    all_latencies.sort()
    n = len(all_latencies)
    p50 = all_latencies[int(n * 0.50)]
    p90 = all_latencies[int(n * 0.90)]
    p99 = all_latencies[int(n * 0.99)]
    mean = statistics.mean(all_latencies)
    qps  = 1000 / mean

    index_size_mb = 0
    for f in ["data/index.json", "data/docs.json", "data/pagerank.json"]:
        if os.path.exists(f):
            index_size_mb += os.path.getsize(f) / (1024 * 1024)

    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)
    print(f"  Queries tested      : {len(TEST_QUERIES)}  ({n_runs} runs each)")
    print(f"  Mean latency        : {mean:.2f} ms")
    print(f"  P50 latency         : {p50:.2f} ms")
    print(f"  P90 latency         : {p90:.2f} ms")
    print(f"  P99 latency         : {p99:.2f} ms")
    print(f"  Throughput          : {qps:.1f} queries/sec")
    print(f"  Index size (total)  : {index_size_mb:.2f} MB")
    print(f"  Documents indexed   : {len(qp.doc_store)}")
    print(f"  Unique terms        : {len(qp.index)}")
    print(f"  PageRank URLs       : {len(qp.pagerank)}")
    print("=" * 70)

    report = {
        "mean_ms": round(mean, 2),
        "p50_ms":  round(p50, 2),
        "p90_ms":  round(p90, 2),
        "p99_ms":  round(p99, 2),
        "qps":     round(qps, 1),
        "index_size_mb": round(index_size_mb, 2),
        "doc_count": len(qp.doc_store),
        "term_count": len(qp.index),
        "queries": query_stats,
    }
    os.makedirs("data", exist_ok=True)
    with open("data/benchmark.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved → data/benchmark.json")
    return report

if __name__ == "__main__":
    run_benchmark(n_runs=3)