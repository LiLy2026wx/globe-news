"""Pure news fetcher — pulls Google News RSS, writes news-data.json.

Standalone script with no HTTP server. Used by:
  - GitHub Actions (daily cron) on the cloud
  - server.py (imports fetch_all) when running locally

Run:  python fetcher.py
Output: news-data.json (overwrites in place, atomic via tmp + rename)
"""
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from urllib.parse import quote

import feedparser

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(PROJECT_DIR, 'news-data.json')

MAX_ITEMS_PER_CELL = 5
REQUEST_DELAY_SECONDS = 0.4
# Google News 搜索默认按相关性排序，会混入几天/几周前的旧闻。
# 用 when: 操作符限定近 N 天，偏向新鲜内容。
RECENCY_WINDOW = '2d'

# (geojson ADMIN key, Chinese display name, ISO_A2)
COUNTRIES = [
    ('China', '中国', 'CN'),
    ('United States of America', '美国', 'US'),
    ('Russia', '俄罗斯', 'RU'),
    ('Japan', '日本', 'JP'),
    ('Germany', '德国', 'DE'),
    ('United Kingdom', '英国', 'GB'),
    ('France', '法国', 'FR'),
    ('India', '印度', 'IN'),
    ('South Korea', '韩国', 'KR'),
    ('Ukraine', '乌克兰', 'UA'),
    ('Israel', '以色列', 'IL'),
    ('Iran', '伊朗', 'IR'),
    ('Turkey', '土耳其', 'TR'),
    ('Saudi Arabia', '沙特', 'SA'),
    ('Brazil', '巴西', 'BR'),
    ('Australia', '澳大利亚', 'AU'),
    ('Canada', '加拿大', 'CA'),
    ('Italy', '意大利', 'IT'),
    ('Spain', '西班牙', 'ES'),
    ('Mexico', '墨西哥', 'MX'),
    ('Indonesia', '印度尼西亚', 'ID'),
    ('Vietnam', '越南', 'VN'),
    ('Thailand', '泰国', 'TH'),
    ('Pakistan', '巴基斯坦', 'PK'),
    ('Egypt', '埃及', 'EG'),
    ('South Africa', '南非', 'ZA'),
    ('Argentina', '阿根廷', 'AR'),
    ('Poland', '波兰', 'PL'),
    ('North Korea', '朝鲜', 'KP'),
    ('Singapore', '新加坡', 'SG'),
]

# (key, display label, query keyword)
CATEGORIES = [
    ('politics', '政治', '政治'),
    ('military', '军事', '军事'),
    ('economy', '经济', '经济'),
    ('technology', '科技', '科技'),
    ('aviation', '航空', '航空航天'),
]


def log(msg):
    # In CI / pythonw, print is the lowest common denominator.
    print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} {msg}', flush=True)


def gnews_rss(query: str) -> str:
    # safe=':' 保留 when:2d 里的冒号不被编码成 %3A
    return f'https://news.google.com/rss/search?q={quote(query, safe=":")}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans'


def humanize_time(published_struct):
    if not published_struct:
        return ''
    try:
        published = datetime(*published_struct[:6], tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - published
        seconds = max(delta.total_seconds(), 0)
        if seconds < 60:
            return '刚刚'
        if seconds < 3600:
            return f'{int(seconds // 60)}分钟前'
        if seconds < 86400:
            return f'{int(seconds // 3600)}小时前'
        days = int(seconds // 86400)
        if days < 7:
            return f'{days}天前'
        return published.strftime('%Y-%m-%d')
    except Exception:
        return ''


def extract_source(entry) -> str:
    src = entry.get('source')
    if isinstance(src, dict):
        return src.get('title', '') or ''
    if src is not None:
        return getattr(src, 'title', '') or ''
    return ''


def fetch_cell(country_zh: str, category_query: str):
    query = f'{country_zh} {category_query} when:{RECENCY_WINDOW}'
    try:
        feed = feedparser.parse(gnews_rss(query))
    except Exception as e:
        log(f'parse failed "{query}": {e}')
        return []
    items = []
    for entry in feed.entries[:MAX_ITEMS_PER_CELL]:
        title = (entry.get('title') or '').strip()
        if not title:
            continue
        source = extract_source(entry)
        if source and title.endswith(' - ' + source):
            title = title[: -(len(source) + 3)].strip()
        items.append({
            'title': title,
            'time': humanize_time(entry.get('published_parsed')),
            'source': source,
            'url': entry.get('link', ''),
        })
    return items


def fetch_all():
    started = datetime.now()
    log(f'Refreshing news: {len(COUNTRIES)} countries x {len(CATEGORIES)} categories')
    data = {
        '_generated': started.isoformat(timespec='seconds'),
        '_countries': len(COUNTRIES),
    }
    for country_key, country_zh, iso in COUNTRIES:
        cell = {'_meta': f'{started.strftime("%Y-%m-%d %H:%M")} · 自动抓取'}
        cell_total = 0
        for cat_key, _, cat_query in CATEGORIES:
            items = fetch_cell(country_zh, cat_query)
            cell[cat_key] = items
            cell_total += len(items)
            time.sleep(REQUEST_DELAY_SECONDS)
        log(f'  {country_zh} {iso}: {cell_total} items')
        data[country_key] = cell

    tmp = OUTPUT_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, OUTPUT_FILE)
    elapsed = (datetime.now() - started).total_seconds()
    log(f'Wrote news-data.json ({elapsed:.1f}s)')


if __name__ == '__main__':
    try:
        fetch_all()
    except Exception:
        log('fetch_all crashed:\n' + traceback.format_exc())
        sys.exit(1)
