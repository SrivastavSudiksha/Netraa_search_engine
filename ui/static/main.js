function toggleTheme() {
    const html = document.documentElement;
    const icon = document.getElementById('theme-icon');
    if (html.getAttribute('data-theme') === 'light') {
        html.setAttribute('data-theme', 'dark');
        icon.classList.replace('fa-moon', 'fa-sun');
        localStorage.setItem('theme', 'dark');
    } else {
        html.setAttribute('data-theme', 'light');
        icon.classList.replace('fa-sun', 'fa-moon');
        localStorage.setItem('theme', 'light');
    }
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('collapsed');
}

function toggleSection(header) {
    const content = header.nextElementSibling;
    const icon = header.querySelector('i');
    content.classList.toggle('hidden');
    icon.classList.toggle('fa-chevron-down');
    icon.classList.toggle('fa-chevron-right');
}

function getTabs() {
    return JSON.parse(sessionStorage.getItem('openTabs') || '[]');
}

function saveTabs(tabs) {
    sessionStorage.setItem('openTabs', JSON.stringify(tabs));
}

function getActiveTabId() {
    return sessionStorage.getItem('activeTabId');
}

function setActiveTabId(id) {
    sessionStorage.setItem('activeTabId', id);
}

function renderTabs() {
    const bar = document.getElementById('tabs-bar');
    if (!bar) return;
    const tabs = getTabs();
    const activeId = getActiveTabId();

    bar.innerHTML = '';
    tabs.forEach(tab => {
        const div = document.createElement('div');
        div.className = 'search-tab' + (tab.id === activeId ? ' active' : '');
        div.innerHTML = `
            <i class="fas fa-search"></i>
            <span class="tab-label">${tab.query}</span>
            <button class="tab-close-btn" onclick="closeTab(event, '${tab.id}')">
                <i class="fas fa-times"></i>
            </button>
        `;
        div.addEventListener('click', () => switchTab(tab.id));
        bar.appendChild(div);
    });

    const newBtn = document.createElement('button');
    newBtn.className = 'new-tab-btn';
    newBtn.innerHTML = '<i class="fas fa-plus"></i>';
    newBtn.onclick = () => {
        document.getElementById('search-input').value = '';
        document.getElementById('search-input').focus();
    };
    bar.appendChild(newBtn);
}

function openTab(query, data) {
    let tabs = getTabs();
    const existing = tabs.find(t => t.query.toLowerCase() === query.toLowerCase());

    if (existing) {
        existing.data = data;
        setActiveTabId(existing.id);
    } else {
        const id = 'tab_' + Date.now();
        tabs.push({ id, query, data });
        setActiveTabId(id);
    }

    saveTabs(tabs);
    renderTabs();
}

function switchTab(id) {
    const tabs = getTabs();
    const tab = tabs.find(t => t.id === id);
    if (!tab) return;
    setActiveTabId(id);
    renderTabs();
    renderResults(tab.data, tab.query);
    document.getElementById('search-input').value = tab.query;
    history.pushState({}, '', `/search?q=${encodeURIComponent(tab.query)}`);
}

function closeTab(e, id) {
    e.stopPropagation();
    let tabs = getTabs();
    const idx = tabs.findIndex(t => t.id === id);
    if (idx === -1) return;

    const wasActive = getActiveTabId() === id;
    tabs.splice(idx, 1);
    saveTabs(tabs);

    if (wasActive) {
        if (tabs.length > 0) {
            const next = tabs[Math.max(0, idx - 1)];
            switchTab(next.id);
        } else {
            setActiveTabId('');
            window.location.href = '/';
        }
    } else {
        renderTabs();
    }
}

function renderResults(data, query) {
    const left = document.getElementById('results-left');
    const right = document.getElementById('results-right');
    if (!left) return;

    if (!data.results || data.results.length === 0) {
        left.innerHTML = `<p class="no-results">No results found for "<strong>${query}</strong>"</p>`;
        right.innerHTML = '';
        return;
    }

    let html = `<p class="results-stats">${data.results.length} results &nbsp;·&nbsp; ${data.elapsed} ms</p>`;
    data.results.forEach(r => {
        const domain = r.url.includes('/') ? r.url.split('/')[2] : r.url;
        html += `
            <div class="result-card">
                <div class="result-url">
                    <span class="result-domain">${domain}</span>
                </div>
                <a href="${r.url}" target="_blank">${r.title}</a>
                <div class="result-snippet">${r.snippet}</div>
            </div>
        `;
    });
    left.innerHTML = html;

    const top = data.results[0];
    right.innerHTML = `
        <div class="knowledge-panel">
            <h2>${top.title}</h2>
            <div class="knowledge-url">${top.url}</div>
            <p class="knowledge-snippet">${top.snippet}</p>
            <a href="${top.url}" target="_blank" class="knowledge-link">
                Visit page <i class="fas fa-external-link-alt"></i>
            </a>
        </div>
    `;
}

async function performSearch(query) {
    if (!query.trim()) return;

    saveRecentSearch(query);

    const resp = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
    const data = await resp.json();

    openTab(query, data);
    renderResults(data, query);
    history.pushState({}, '', `/search?q=${encodeURIComponent(query)}`);
}

function saveRecentSearch(query) {
    let recent = JSON.parse(localStorage.getItem('recent') || '[]');
    recent = recent.filter(s => s.toLowerCase() !== query.toLowerCase());
    recent.unshift(query);
    if (recent.length > 10) recent.pop();
    localStorage.setItem('recent', JSON.stringify(recent));
    renderRecentSearches();
}

function renderRecentSearches() {
    const container = document.getElementById('recent-searches');
    if (!container) return;
    const recent = JSON.parse(localStorage.getItem('recent') || '[]');
    container.innerHTML = '';
    recent.forEach(s => {
        const a = document.createElement('a');
        a.href = '#';
        a.className = 'recent-item';
        a.innerHTML = `<i class="fas fa-history"></i> ${s}`;
        a.addEventListener('click', (e) => {
            e.preventDefault();
            document.getElementById('search-input').value = s;
            performSearch(s);
        });
        container.appendChild(a);
    });
}

const savedTheme = localStorage.getItem('theme') || 'light';
document.documentElement.setAttribute('data-theme', savedTheme);
const themeIcon = document.getElementById('theme-icon');
if (savedTheme === 'dark' && themeIcon) themeIcon.classList.replace('fa-moon', 'fa-sun');

document.addEventListener('DOMContentLoaded', () => {
    renderRecentSearches();
    renderTabs();

    const form = document.getElementById('search-form');
    if (form) {
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            const query = document.getElementById('search-input').value;
            performSearch(query);
        });
    }

    const urlQuery = new URLSearchParams(window.location.search).get('q');
    if (urlQuery && getTabs().length === 0) {
        saveRecentSearch(urlQuery);
        openTab(urlQuery, {
            results: window.initialResults || [],
            elapsed: window.initialElapsed || 0
        });
    } else if (urlQuery) {
        const tabs = getTabs();
        const match = tabs.find(t => t.query.toLowerCase() === urlQuery.toLowerCase());
        if (match) {
            setActiveTabId(match.id);
            renderTabs();
        }
    }
});