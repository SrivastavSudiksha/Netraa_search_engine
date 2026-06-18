from collections import deque
import threading

class URLFrontier:
    def __init__(self, seed_urls):
        self.queue = deque()
        self.visited = set()
        self.in_queue = set()
        self.lock = threading.Lock()
        for url in seed_urls:
            self.add_url(url)

    def add_url(self, url):
        with self.lock:
            if url not in self.visited and url not in self.in_queue:
                self.queue.append(url)
                self.in_queue.add(url)

    def get_url(self):
        with self.lock:
            while self.queue:
                url = self.queue.popleft()
                self.in_queue.discard(url)
                if url not in self.visited:
                    self.visited.add(url)
                    return url
        return None

    def has_urls(self):
        return len(self.queue) > 0

    def size(self):
        return len(self.visited)