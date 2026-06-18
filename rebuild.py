import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawler.crawler import SearchCrawler
from indexer.indexer import InvertedIndex

crawler = SearchCrawler(max_pages=300)
pages = asyncio.run(crawler.run())

index = InvertedIndex()
index.build(pages)
index.compute_bm25()
index.save()
print(f"Done — {len(pages)} pages crawled, {index.doc_count} docs indexed")