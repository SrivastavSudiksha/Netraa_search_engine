import aiohttp
import asyncio
import json
import gzip
import io
import logging
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

CC_INDEX = "https://index.commoncrawl.org/CC-MAIN-2024-51-index"

async def search_cdx(session, query_url_pattern, max_results=5):
    params = {
        "url": query_url_pattern,
        "output": "json",
        "limit": max_results,
        "filter": "status:200",
        "fl": "url,title,timestamp,filename,offset,length"
    }
    try:
        async with session.get(CC_INDEX, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return []
            text = await resp.text()
            results = []
            for line in text.strip().split('\n'):
                if line:
                    try:
                        results.append(json.loads(line))
                    except:
                        pass
            return results
    except Exception as e:
        logger.warning(f"CDX error: {e}")
        return []

async def fetch_warc_page(session, filename, offset, length):
    url = f"https://data.commoncrawl.org/{filename}"
    headers = {"Range": f"bytes={offset}-{int(offset) + int(length) - 1}"}
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status in (200, 206):
                raw = await resp.read()
                try:
                    raw = gzip.decompress(raw)
                except:
                    pass
                text = raw.decode('utf-8', errors='ignore')
                parts = text.split('\r\n\r\n', 2)
                html = parts[2] if len(parts) >= 3 else text
                return html
    except Exception as e:
        logger.warning(f"WARC fetch error: {e}")
    return None

def extract_text(url, html):
    try:
        soup = BeautifulSoup(html, 'lxml')
        title = soup.title.string.strip() if soup.title and soup.title.string else url
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()
        main = soup.find('main') or soup.find('article') or soup.find('div', id='content') or soup
        text = ' '.join(main.get_text().split())
        content = text[:5000]
        snippet = content[:220].rsplit(' ', 1)[0] + '…' if len(content) > 220 else content
        return {'url': url, 'title': title, 'content': content, 'snippet': snippet}
    except:
        return None

async def fetch_from_commoncrawl(keywords, max_results=10):
    results = []
    async with aiohttp.ClientSession(headers={'User-Agent': 'Netraa-Bot/1.0'}) as session:
        tasks = []
        for keyword in keywords[:3]:
            pattern = f"*.com/*{keyword}*"
            tasks.append(search_cdx(session, pattern, max_results=3))
            tasks.append(search_cdx(session, f"en.wikipedia.org/wiki/*{keyword}*", max_results=3))

        cdx_results = await asyncio.gather(*tasks)
        all_records = []
        for batch in cdx_results:
            all_records.extend(batch)

        seen_urls = set()
        fetch_tasks = []
        for record in all_records:
            url = record.get('url', '')
            if url in seen_urls:
                continue
            seen_urls.add(url)
            if 'filename' in record and 'offset' in record and 'length' in record:
                fetch_tasks.append((url, record['filename'], record['offset'], record['length']))

        async def fetch_and_parse(url, filename, offset, length):
            html = await fetch_warc_page(session, filename, offset, length)
            if html:
                return extract_text(url, html)
            return None

        page_tasks = [fetch_and_parse(u, f, o, l) for u, f, o, l in fetch_tasks[:max_results]]
        pages = await asyncio.gather(*page_tasks)
        results = [p for p in pages if p]

    return results