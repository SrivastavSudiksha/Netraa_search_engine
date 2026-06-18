import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify
import time
from query.processor import QueryProcessor

app = Flask(__name__)
qp = QueryProcessor()
qp.load()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search')
def search():
    query = request.args.get('q', '')
    start = time.time()
    results = qp.search(query) if query else []
    elapsed = round((time.time() - start) * 1000, 2)
    return render_template('index.html', query=query, results=results, elapsed=elapsed)

@app.route('/api/search')
def api_search():
    query = request.args.get('q', '')
    start = time.time()
    results = qp.search(query) if query else []
    elapsed = round((time.time() - start) * 1000, 2)
    return jsonify({
        'query': query,
        'results': results,
        'elapsed': elapsed,
        'count': len(results)
    })

if __name__ == '__main__':
    app.run(debug=True)