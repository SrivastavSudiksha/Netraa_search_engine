import urllib.robotparser
from functools import lru_cache
from urllib.parse import urlparse

@lru_cache(maxsize=500)
def get_parser(base_url):
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(base_url + "/robots.txt")
    try:
        rp.read()
    except:
        pass
    return rp

def is_allowed(url):
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    rp = get_parser(base)
    return rp.can_fetch("*", url)