import json
import os
import math
from collections import defaultdict
from indexer.parser import process_document

class InvertedIndex:
    def __init__(self):
        self.index = defaultdict(list)
        self.doc_store = {}
        self.doc_count = 0
        self.avg_doc_length = 0

    def build(self, crawled_pages):
        tf_store = {}
        total_tokens = 0

        for doc in crawled_pages:
            processed = process_document(doc)
            doc_id = self.doc_count
            content = doc.get('content', '')
            snippet = content[:220].rsplit(' ', 1)[0] + '…' if len(content) > 220 else content
            token_count = len(processed['tokens'])
            total_tokens += token_count

            self.doc_store[doc_id] = {
                'url': processed['url'],
                'title': processed['title'],
                'snippet': snippet,
                'token_count': token_count
            }

            tf = defaultdict(int)
            for token in processed['tokens']:
                tf[token] += 1
            tf_store[doc_id] = tf
            self.doc_count += 1

        self.avg_doc_length = total_tokens / max(self.doc_count, 1)

        for doc_id, tf in tf_store.items():
            total = self.doc_store[doc_id]['token_count']
            for term, count in tf.items():
                self.index[term].append((doc_id, count, total))

    def compute_bm25(self, k1=1.5, b=0.75):
        new_index = defaultdict(list)
        for term, postings in self.index.items():
            df = len(postings)
            idf = math.log((self.doc_count - df + 0.5) / (df + 0.5) + 1)
            scored = []
            for doc_id, tf, doc_len in postings:
                norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_len / self.avg_doc_length))
                scored.append((doc_id, idf * norm))
            scored.sort(key=lambda x: x[1], reverse=True)
            new_index[term] = scored
        self.index = new_index

    def save(self, index_path='data/index.json', docs_path='data/docs.json'):
        os.makedirs('data', exist_ok=True)
        with open(index_path, 'w') as f:
            json.dump(dict(self.index), f)
        with open(docs_path, 'w') as f:
            json.dump(self.doc_store, f)
        with open('data/meta.json', 'w') as f:
            json.dump({'doc_count': self.doc_count, 'avg_doc_length': self.avg_doc_length}, f)

    def load(self, index_path='data/index.json', docs_path='data/docs.json'):
        with open(index_path, 'r') as f:
            self.index = defaultdict(list, json.load(f))
        with open(docs_path, 'r') as f:
            raw = json.load(f)
            self.doc_store = {int(k): v for k, v in raw.items()}
        self.doc_count = len(self.doc_store)
        try:
            with open('data/meta.json', 'r') as f:
                meta = json.load(f)
                self.avg_doc_length = meta.get('avg_doc_length', 0)
        except:
            self.avg_doc_length = 0

if __name__ == "__main__":
    with open('data/crawled_pages.json', 'r') as f:
        pages = json.load(f)

    index = InvertedIndex()
    index.build(pages)
    index.compute_bm25()
    index.save()
    print(f"BM25 Index built — {len(index.index)} terms, {index.doc_count} docs, avg_len={index.avg_doc_length:.1f}")