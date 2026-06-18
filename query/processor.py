import json
import asyncio
import logging
from collections import defaultdict
from indexer.parser import tokenize, stem

logger = logging.getLogger(__name__)

ALPHA = 0.8


class QueryProcessor:
    def __init__(self):
        self.index: dict = {}
        self.doc_store: dict = {}
        self.pagerank: dict[str, float] = {}

    def load(self, index_path="data/index.json", docs_path="data/docs.json", pr_path="data/pagerank.json"):
        with open(index_path) as f:
            self.index = json.load(f)
        with open(docs_path) as f:
            raw = json.load(f)
            self.doc_store = {int(k): v for k, v in raw.items()}
        try:
            with open(pr_path) as f:
                self.pagerank = json.load(f)
            logger.info(f"PageRank loaded — {len(self.pagerank)} URLs")
        except FileNotFoundError:
            logger.warning("pagerank.json not found — running BM25-only mode")
            self.pagerank = {}

    def _bm25_scores(self, tokens):
        scores = defaultdict(float)
        for token in tokens:
            if token in self.index:
                for doc_id, bm25 in self.index[token]:
                    scores[int(doc_id)] += bm25
        return scores

    def _blend(self, bm25_scores):
        if not bm25_scores:
            return []
        max_bm25 = max(bm25_scores.values()) or 1.0
        norm_bm25 = {doc_id: s / max_bm25 for doc_id, s in bm25_scores.items()}
        blended = []
        for doc_id, nbm25 in norm_bm25.items():
            url = self.doc_store.get(doc_id, {}).get("url", "")
            pr_score = self.pagerank.get(url, 0.0)
            final = ALPHA * nbm25 + (1.0 - ALPHA) * pr_score
            blended.append((doc_id, final))
        return sorted(blended, key=lambda x: x[1], reverse=True)

    def _local_search(self, tokens, top_k=10):
        bm25_scores = self._bm25_scores(tokens)
        ranked = self._blend(bm25_scores)
        results = []
        for doc_id, score in ranked[:top_k]:
            doc = self.doc_store.get(doc_id, {})
            url = doc.get("url", "")
            results.append({
                "url":      url,
                "title":    doc.get("title", "Untitled"),
                "snippet":  doc.get("snippet", ""),
                "score":    round(score, 4),
                "bm25":     round(bm25_scores.get(doc_id, 0.0), 4),
                "pagerank": round(self.pagerank.get(url, 0.0), 4),
                "source":   "local",
            })
        return results

    def _commoncrawl_search(self, keywords, max_results=5):
        try:
            from crawler.common_crawl import fetch_from_commoncrawl
            pages = asyncio.run(
                asyncio.wait_for(
                    fetch_from_commoncrawl(keywords, max_results=max_results),
                    timeout=4.0,
                )
            )
            return [{
                "url":      p.get("url", ""),
                "title":    p.get("title", "Untitled"),
                "snippet":  p.get("snippet", ""),
                "score":    0.0,
                "bm25":     0.0,
                "pagerank": 0.0,
                "source":   "commoncrawl",
            } for p in pages]
        except Exception:
            return []

    def search(self, query, top_k=10):
        tokens   = [stem(t) for t in tokenize(query)]
        keywords = list(set(tokenize(query)))
        local_results = self._local_search(tokens, top_k=top_k)
        if len(local_results) >= 5:
            return local_results[:top_k]
        seen_urls  = {r["url"] for r in local_results}
        needed     = top_k - len(local_results)
        cc_results = self._commoncrawl_search(keywords, max_results=needed + 3)
        fresh = [r for r in cc_results if r["url"] not in seen_urls]
        return (local_results + fresh)[:top_k]