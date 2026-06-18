import asyncio
import aiohttp
import os
import json
import time
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from crawler.frontier import URLFrontier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEED_URLS = [
    "https://en.wikipedia.org/wiki/Python_(programming_language)",
    "https://en.wikipedia.org/wiki/Artificial_intelligence",
    "https://en.wikipedia.org/wiki/Cricket",
    "https://en.wikipedia.org/wiki/Cooking",
    "https://en.wikipedia.org/wiki/Film",
    "https://www.bbc.com/news",
    "https://www.bbc.com/sport",
    "https://www.geeksforgeeks.org/python-programming-language/",
    "https://docs.python.org/3/tutorial/index.html",
    "https://www.allrecipes.com/",
    "https://www.espn.com/",
    "https://www.nationalgeographic.com/",
    "https://www.healthline.com/",
    "https://www.investopedia.com/",
    "https://www.nytimes.com/section/technology",
    "https://techcrunch.com/",
    "https://www.theguardian.com/international",
    "https://www.cnn.com/world",
    "https://www.foodnetwork.com/",
    "https://www.goodreads.com/",
    "https://www.rottentomatoes.com/",
    "https://www.billboard.com/",
    "https://www.wired.com/",
    "https://www.sciencedaily.com/",
    "https://www.history.com/",
]

class SearchCrawler:
    def __init__(self, seed_urls=None, max_pages=5000, max_concurrent=15):
        self.frontier = URLFrontier(seed_urls or SEED_URLS)
        self.max_pages = max_pages
        self.semaphore = None
        self.max_concurrent = max_concurrent
        self.crawled_data = []
        self.robots_cache = {}
        self.domain_count = {}
        self.max_per_domain = 1000

    def _get_domain(self, url):
        return urlparse(url).netloc

    async def can_fetch(self, session, url):
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        if robots_url not in self.robots_cache:
            try:
                async with session.get(robots_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    content = await resp.text()
                    rp = RobotFileParser()
                    rp.parse(content.splitlines())
                    self.robots_cache[robots_url] = rp
            except:
                self.robots_cache[robots_url] = None
        rp = self.robots_cache.get(robots_url)
        return rp.can_fetch("*", url) if rp else True

    async def fetch_page(self, session, url):
        async with self.semaphore:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:  # 10 → 15
                    if response.status == 200:
                        ct = response.headers.get('Content-Type', '')
                        if 'text/html' in ct:
                            return await response.text()
            except Exception as e:
                logger.warning(f"Failed: {url} — {e}")
            return None

    def parse_page(self, url, html):
        soup = BeautifulSoup(html, 'lxml')
        title = soup.title.string.strip() if soup.title and soup.title.string else url
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            tag.decompose()
        main = soup.find('main') or soup.find('article') or soup.find('div', id='content') or soup
        text = ' '.join(main.get_text().split())
        links = []
        for a_tag in soup.find_all('a', href=True):
            full_url = urljoin(url, a_tag['href'])
            full_url = full_url.split('#')[0]
            parsed = urlparse(full_url)
            if full_url.startswith('http') and not parsed.path.endswith(
                ('.pdf', '.zip', '.jpg', '.png', '.gif', '.mp4', '.exe', '.svg', '.css', '.js')
            ):
                links.append(full_url)
        return {
            'url': url,
            'title': title,
            'content': text[:5000],
            'links': links[:30],
            'timestamp': time.time()
        }

    async def crawl_url(self, session, url):
        domain = self._get_domain(url)
        if self.domain_count.get(domain, 0) >= self.max_per_domain:
            return
        if not await self.can_fetch(session, url):
            return
        html = await self.fetch_page(session, url)
        if not html:
            return
        page_data = self.parse_page(url, html)
        self.crawled_data.append(page_data)
        self.domain_count[domain] = self.domain_count.get(domain, 0) + 1
        for link in page_data['links']:
            if len(self.crawled_data) < self.max_pages:
                self.frontier.add_url(link)
        logger.info(f"✅ [{len(self.crawled_data)}] {url}")

    async def run(self):
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        async with aiohttp.ClientSession(
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        ) as session:
            stall_count = 0
            prev_crawled = 0
            while len(self.crawled_data) < self.max_pages:
                if not self.frontier.has_urls():
                    logger.info("Frontier empty, stopping.")
                    break

                batch = []
                for _ in range(20):
                    url = self.frontier.get_url()
                    if url is None:
                        break
                    batch.append(url)

                if not batch:
                    stall_count += 1
                    if stall_count >= 5:
                        logger.info("No progress after 5 attempts, stopping.")
                        break
                    await asyncio.sleep(1)
                    continue

                await asyncio.gather(*[self.crawl_url(session, url) for url in batch])

                if len(self.crawled_data) == prev_crawled:
                    stall_count += 1
                    if stall_count >= 30:
                        logger.info("Crawl stalled, stopping.")
                        break
                else:
                    stall_count = 0
                    prev_crawled = len(self.crawled_data)

        logger.info(f"Frontier remaining: {len(self.frontier.queue)}, Visited: {len(self.frontier.visited)}")
        os.makedirs('data', exist_ok=True)
        with open('data/crawled_pages.json', 'w') as f:
            json.dump(self.crawled_data, f, indent=2)
        logger.info(f"🎉 Done! Crawled {len(self.crawled_data)} pages")
        return self.crawled_data