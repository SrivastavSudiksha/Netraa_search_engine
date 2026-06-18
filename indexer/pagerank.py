import json
import os
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class PageRank:
    def __init__(self, damping=0.85, max_iter=100, tolerance=1e-6):
        self.damping = damping
        self.max_iter = max_iter
        self.tolerance = tolerance
        self.url_to_id: dict[str, int] = {}
        self.id_to_url: dict[int, str] = {}
        self.out_links: dict[int, list[int]] = defaultdict(list)
        self.in_links:  dict[int, list[int]] = defaultdict(list)
        self.scores:    dict[int, float] = {}

    def _get_or_add(self, url: str) -> int:
        if url not in self.url_to_id:
            nid = len(self.url_to_id)
            self.url_to_id[url] = nid
            self.id_to_url[nid] = url
        return self.url_to_id[url]

    def build_graph(self, crawled_pages: list[dict]) -> None:
        crawled_urls = {p["url"] for p in crawled_pages}
        for page in crawled_pages:
            src = self._get_or_add(page["url"])
            for link in page.get("links", []):
                if link in crawled_urls and link != page["url"]:
                    dst = self._get_or_add(link)
                    if dst not in self.out_links[src]:
                        self.out_links[src].append(dst)
                        self.in_links[dst].append(src)
        n = len(self.url_to_id)
        logger.info(f"Graph built — {n} nodes, {sum(len(v) for v in self.out_links.values())} edges")

    def compute(self) -> dict[str, float]:
        n = len(self.url_to_id)
        if n == 0:
            return {}

        pr = {nid: 1.0 / n for nid in range(n)}
        dangling = [nid for nid in range(n) if not self.out_links[nid]]

        for iteration in range(self.max_iter):
            dangling_sum = sum(pr[nid] for nid in dangling)
            dangling_contrib = self.damping * dangling_sum / n
            new_pr: dict[int, float] = {}
            for nid in range(n):
                rank = (1.0 - self.damping) / n + dangling_contrib
                for src in self.in_links[nid]:
                    out_degree = len(self.out_links[src])
                    if out_degree > 0:
                        rank += self.damping * pr[src] / out_degree
                new_pr[nid] = rank
            delta = sum(abs(new_pr[nid] - pr[nid]) for nid in range(n))
            pr = new_pr
            if delta < self.tolerance:
                logger.info(f"PageRank converged in {iteration + 1} iterations (delta={delta:.2e})")
                break
        else:
            logger.warning(f"PageRank did not converge after {self.max_iter} iterations")

        max_score = max(pr.values()) or 1.0
        self.scores = {nid: pr[nid] / max_score for nid in range(n)}
        return {self.id_to_url[nid]: self.scores[nid] for nid in range(n)}

    def save(self, path: str = "data/pagerank.json") -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {self.id_to_url[nid]: self.scores[nid] for nid in self.scores}
        with open(path, "w") as f:
            json.dump(data, f)
        logger.info(f"PageRank scores saved → {path}")

    @staticmethod
    def load(path: str = "data/pagerank.json") -> dict[str, float]:
        if not os.path.exists(path):
            return {}
        with open(path) as f:
            return json.load(f)

    def top_pages(self, n: int = 10) -> list[tuple[str, float]]:
        ranked = sorted(
            ((self.id_to_url[nid], self.scores[nid]) for nid in self.scores),
            key=lambda x: x[1], reverse=True,
        )
        return ranked[:n]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    crawl_path = "data/crawled_pages.json"
    if not os.path.exists(crawl_path):
        print(f"ERROR: {crawl_path} not found — run rebuild.py first.")
        raise SystemExit(1)

    with open(crawl_path) as f:
        pages = json.load(f)

    pr = PageRank()
    pr.build_graph(pages)
    scores = pr.compute()
    pr.save()

    print("\nTop 10 pages by PageRank:")
    print("-" * 60)
    for rank, (url, score) in enumerate(pr.top_pages(10), 1):
        print(f"  {rank:>2}. {score:.4f}  {url}")
    print(f"\nTotal nodes scored: {len(scores)}")