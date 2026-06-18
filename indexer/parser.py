import re
from bs4 import BeautifulSoup

STOPWORDS = set([
    'a', 'an', 'the', 'is', 'it', 'in', 'on', 'at', 'to', 'for',
    'of', 'and', 'or', 'but', 'with', 'this', 'that', 'was', 'are',
    'be', 'by', 'as', 'from', 'has', 'have', 'had', 'not', 'they',
    'we', 'you', 'he', 'she', 'his', 'her', 'its', 'our', 'their'
])

def tokenize(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    tokens = text.split()
    return [t for t in tokens if t not in STOPWORDS and len(t) > 2]

def stem(word):
    suffixes = ['ing', 'tion', 'ed', 'ly', 'er', 'est', 'ness', 'ment']
    for suffix in suffixes:
        if word.endswith(suffix) and len(word) - len(suffix) > 3:
            return word[:-len(suffix)]
    return word

def process_document(doc):
    tokens = tokenize(doc['content'])
    stemmed = [stem(t) for t in tokens]
    return {
        'url': doc['url'],
        'title': doc['title'],
        'tokens': stemmed,
        'raw_tokens': tokens
    }