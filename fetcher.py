"""Pure news fetcher — pulls Google News RSS, writes news-data.json.

Standalone script with no HTTP server. Used by:
  - GitHub Actions (daily cron) on the cloud
  - server.py (imports fetch_all) when running locally

Run:  python fetcher.py
Output: news-data.json (overwrites in place, atomic via tmp + rename)
"""
import json
import os
import re
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import feedparser
import requests

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(PROJECT_DIR, 'news-data.json')
# 省级下钻：中国各省"综合热点"，单独成文件，前端下钻时才加载。
CN_GEOJSON = os.path.join(PROJECT_DIR, 'assets', 'china-provinces.geojson')
CN_OUTPUT_FILE = os.path.join(PROJECT_DIR, 'news-cn.json')
MAX_PROVINCE_ITEMS = 8
RECENCY_HOT_HOURS = 12  # 省级热度 = 近这么多小时内发布的条数

# 显示用时间一律北京时区。Actions runner 是 UTC，若用裸 datetime.now()
# 存出来的 _generated/_meta 会比北京时间慢 8 小时，前端显示成"昨天"。
BJT = timezone(timedelta(hours=8))

MAX_ITEMS_PER_CELL = 5
REQUEST_DELAY_SECONDS = 0.4
# Google News 搜索默认按相关性排序，会混入几天/几周前的旧闻。
# 用 when: 操作符限定近 N 天，偏向新鲜内容。
RECENCY_WINDOW = '2d'

# Google News RSS 给的是 news.google.com 跳转链接，国内/微信打不开（黑屏跳回）。
# 抓取时（Actions 能访问 Google）把它解码成真实文章地址，存直链。
RESOLVE_WORKERS = 8
RESOLVE_TIMEOUT = 20
_HTTP = requests.Session()
_HTTP.headers['User-Agent'] = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/124.0 Safari/537.36'
)

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


def baidu_search_url(title: str) -> str:
    # 兜底：解码失败时跳百度搜索该标题，国内必定可开。
    return f'https://www.baidu.com/s?wd={quote(title)}'


# 国内被墙的常见外媒域名：即便解出真实直链也打不开，统一转百度搜索同题报道。
BLOCKED_DOMAINS = (
    'bbc.com', 'bbc.co.uk', 'rfi.fr', 'dw.com', 'rfa.org',
    'voachinese.com', 'voanews.com', 'nytimes.com', 'nyt.com',
    'wsj.com', 'reuters.com', 'bloomberg.com', 'theguardian.com',
    'ft.com', 'economist.com', 'youtube.com', 'x.com', 'twitter.com',
    'facebook.com', 'wikipedia.org', 't.me',
)


def is_blocked(real_url: str) -> bool:
    host = re.sub(r'^https?://', '', real_url).split('/', 1)[0].lower()
    return any(host == d or host.endswith('.' + d) for d in BLOCKED_DOMAINS)


def resolve_gnews_url(url: str, title: str) -> str:
    """把 news.google.com 跳转链接解码成真实文章直链。

    走 Google 内部 batchexecute 接口（非公开，未来可能变）。任何失败都兜底为
    百度搜索链接——绝不返回打不开的 google 链接。非 google 链接原样返回。
    """
    if 'news.google.com' not in url or '/articles/' not in url:
        return url
    try:
        art = url.split('/articles/')[1].split('?')[0]
        page = _HTTP.get(
            f'https://news.google.com/rss/articles/{art}', timeout=RESOLVE_TIMEOUT
        ).text
        sg = re.search(r'data-n-a-sg="([^"]+)"', page).group(1)
        ts = re.search(r'data-n-a-ts="([^"]+)"', page).group(1)
        inner = (
            '["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,'
            'null,null,null,null,null,0,1],"X","X",1,[1,1,1],1,1,null,0,0,null,0],'
            f'"{art}",{ts},"{sg}"]'
        )
        freq = json.dumps([[['Fbv4je', inner, None, 'generic']]])
        resp = _HTTP.post(
            'https://news.google.com/_/DotsSplashUi/data/batchexecute',
            data='f.req=' + quote(freq),
            headers={'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'},
            timeout=RESOLVE_TIMEOUT,
        ).text
        line = next(l for l in resp.split('\n') if l.startswith('[['))
        real = json.loads(json.loads(line)[0][2])[1]
        if real and real.startswith('http'):
            return baidu_search_url(title) if is_blocked(real) else real
    except Exception as e:
        log(f'resolve failed ({title[:20]}): {e}')
    return baidu_search_url(title)


def resolve_all_urls(items):
    """并发把一批 item 的 google 链接换成真实直链（原地修改）。"""
    targets = [it for it in items if 'news.google.com' in it.get('url', '')]
    if not targets:
        return
    log(f'Resolving {len(targets)} Google News links → real URLs ({RESOLVE_WORKERS} workers)...')
    started = time.time()

    def work(it):
        it['url'] = resolve_gnews_url(it['url'], it.get('title', ''))

    with ThreadPoolExecutor(max_workers=RESOLVE_WORKERS) as pool:
        list(pool.map(work, targets))
    baidu = sum(1 for it in targets if it['url'].startswith('https://www.baidu.com/s'))
    log(f'Resolved {len(targets)} links in {time.time() - started:.1f}s '
        f'({len(targets) - baidu} direct, {baidu} fell back to Baidu search)')


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
    """返回 (展示用的前 N 条, 该查询近 2 天命中的原始总条数)。

    原始总条数 = 该国该类的"热度"信号（远比留下的 5 条更能区分大小国），
    用来驱动地球上光柱的高低。
    """
    query = f'{country_zh} {category_query} when:{RECENCY_WINDOW}'
    try:
        feed = feedparser.parse(gnews_rss(query))
    except Exception as e:
        log(f'parse failed "{query}": {e}')
        return [], 0
    raw_count = len(feed.entries)
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
    return items, raw_count


def fetch_all():
    started = datetime.now(BJT)
    log(f'Refreshing news: {len(COUNTRIES)} countries x {len(CATEGORIES)} categories')
    data = {
        '_generated': started.isoformat(timespec='seconds'),
        '_countries': len(COUNTRIES),
    }
    all_items = []
    for country_key, country_zh, iso in COUNTRIES:
        cell = {'_meta': f'{started.strftime("%Y-%m-%d %H:%M")} · 自动抓取'}
        cell_total = 0
        intensity = {}  # 按类别的近2天原始命中数；驱动光柱高度(总和)+颜色(主导类)
        for cat_key, _, cat_query in CATEGORIES:
            items, raw_count = fetch_cell(country_zh, cat_query)
            cell[cat_key] = items
            all_items.extend(items)
            cell_total += len(items)
            intensity[cat_key] = raw_count
            time.sleep(REQUEST_DELAY_SECONDS)
        cell['_intensity'] = intensity
        log(f'  {country_zh} {iso}: {cell_total} items (intensity {sum(intensity.values())})')
        data[country_key] = cell

    resolve_all_urls(all_items)

    tmp = OUTPUT_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, OUTPUT_FILE)
    elapsed = (datetime.now(BJT) - started).total_seconds()
    log(f'Wrote news-data.json ({elapsed:.1f}s)')


_PROV_SUFFIXES = (
    '维吾尔自治区', '壮族自治区', '回族自治区', '自治区',
    '特别行政区', '省', '市',
)


def province_query_name(name: str) -> str:
    """省级行政区全名 → 适合搜索的短名。北京市→北京 / 新疆维吾尔自治区→新疆。"""
    for suf in _PROV_SUFFIXES:  # 长后缀在前，避免"自治区"先吃掉"维吾尔自治区"
        if name.endswith(suf):
            return name[: -len(suf)]
    return name


def fetch_province_cell(query_name: str):
    """单个省的'综合热点'：不分类，取近2天前 N 条 + 热度。

    热度不能用 len(feed.entries)——省名是常见词，单查询基本都撞 100 上限、毫无
    区分度。改用'近 12 小时内发布的条数'近似新闻速度：活跃省多、安静省少，天然不饱和。
    """
    query = f'{query_name} when:{RECENCY_WINDOW}'
    try:
        feed = feedparser.parse(gnews_rss(query))
    except Exception as e:
        log(f'parse failed "{query}": {e}')
        return [], 0
    now = datetime.now(timezone.utc)
    hot = 0
    for entry in feed.entries:
        pp = entry.get('published_parsed')
        if not pp:
            continue
        age_h = (now - datetime(*pp[:6], tzinfo=timezone.utc)).total_seconds() / 3600
        if age_h < RECENCY_HOT_HOURS:
            hot += 1
    items = []
    for entry in feed.entries[:MAX_PROVINCE_ITEMS]:
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
    return items, hot


def fetch_cn_provinces():
    """抓中国各省综合热点 → news-cn.json。省名取自 china-provinces.geojson。"""
    try:
        with open(CN_GEOJSON, encoding='utf-8') as f:
            geo = json.load(f)
    except Exception as e:
        log(f'skip CN provinces (no geojson): {e}')
        return
    names = [
        feat['properties']['name']
        for feat in geo.get('features', [])
        if feat.get('properties', {}).get('level') == 'province'
        and feat['properties'].get('name')
    ]
    started = datetime.now(BJT)
    log(f'Refreshing CN provinces: {len(names)} regions')
    meta = f'{started.strftime("%Y-%m-%d %H:%M")} · 自动抓取'
    out = {
        '_generated': started.isoformat(timespec='seconds'),
        '_kind': 'cn-provinces',
        'provinces': {},
    }
    all_items = []
    for name in names:
        items, hot = fetch_province_cell(province_query_name(name))
        out['provinces'][name] = {'_intensity': hot, '_meta': meta, 'items': items}
        all_items.extend(items)
        time.sleep(REQUEST_DELAY_SECONDS)
    log(f'  CN provinces fetched: {sum(len(p["items"]) for p in out["provinces"].values())} items')

    resolve_all_urls(all_items)

    tmp = CN_OUTPUT_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CN_OUTPUT_FILE)
    elapsed = (datetime.now(BJT) - started).total_seconds()
    log(f'Wrote news-cn.json ({elapsed:.1f}s)')


if __name__ == '__main__':
    try:
        fetch_all()
        fetch_cn_provinces()
    except Exception:
        log('fetch crashed:\n' + traceback.format_exc())
        sys.exit(1)
