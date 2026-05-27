"""Daily WeChat push via Server酱 Turbo (sct.ftqq.com).

Reads SENDKEY from (in priority order):
  1. env SCT_SENDKEY      (used by GitHub Actions secrets)
  2. config.json          (used for local testing)

Reads site URL from:
  1. env SITE_URL         (cloud: https://your-project.pages.dev)
  2. fallback: http://{LAN_IP}:8765/   (local development)

Setup ONCE:
  1. Open https://sct.ftqq.com/ → scan with WeChat → follow the official account
     → copy your SENDKEY (looks like 'SCT123abc...')
  2. EITHER set env var SCT_SENDKEY
     OR save it next to this file as config.json:
        { "sct_sendkey": "SCTxxxxxxxx" }
  3. Run:  python push.py
"""
import json
import os
import socket
import sys
import urllib.parse
import urllib.request
from datetime import datetime

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(PROJECT_DIR, 'config.json')
LOCAL_PORT = 8765


def get_lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.254.254.254', 1))
        return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'
    finally:
        s.close()


def load_sendkey() -> str:
    key = os.environ.get('SCT_SENDKEY', '').strip()
    if key:
        return key
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return (json.load(f).get('sct_sendkey') or '').strip()
        except Exception as e:
            print(f'[WARN] Cannot read config.json: {e}')
    return ''


def resolve_url() -> tuple[str, bool]:
    """Returns (url, is_cloud)."""
    site = os.environ.get('SITE_URL', '').strip().rstrip('/')
    if site:
        return site + '/', True
    return f'http://{get_lan_ip()}:{LOCAL_PORT}/', False


def send_serverchan(sendkey: str, title: str, desp: str) -> dict:
    url = f'https://sctapi.ftqq.com/{sendkey}.send'
    data = urllib.parse.urlencode({'title': title, 'desp': desp}).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST')
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode('utf-8'))


def main() -> int:
    sendkey = load_sendkey()
    if not sendkey:
        print('[ERROR] SCT_SENDKEY 未配置。')
        print('  1. 访问 https://sct.ftqq.com/ ，扫码绑定微信，复制 SENDKEY')
        print('  2. 设置环境变量 SCT_SENDKEY，或在 config.json 写入 {"sct_sendkey": "你的KEY"}')
        print('  3. 重新运行 python push.py')
        return 1

    url, is_cloud = resolve_url()
    now = datetime.now()

    title = f'每日新闻地球仪 · {now.strftime("%m月%d日")}'

    if is_cloud:
        access_note = '随时随地打开（无需家中 PC 开机）'
    else:
        access_note = f'链接仅在家中 WiFi 可访问（{url}）'

    desp = (
        '### 今日要闻已就位\n\n'
        '点击进入互动地球仪，浏览全球 30 个国家的'
        '**政治 · 军事 · 经济 · 科技 · 航空** 五大类要闻。\n\n'
        f'## [打开新闻地球仪 →]({url})\n\n'
        '---\n\n'
        f'- {access_note}\n'
        f'- 更新于：{now.strftime("%Y-%m-%d %A %H:%M")}\n'
        '- 数据源：Google News RSS · 每日刷新\n'
    )

    try:
        result = send_serverchan(sendkey, title, desp)
    except Exception as e:
        print(f'[ERROR] HTTP failed: {e}')
        return 2

    if result.get('code') == 0:
        print(f'[OK] Pushed to WeChat. URL in message: {url}')
        return 0
    else:
        print(f'[FAIL] Server酱 returned: {result}')
        return 3


if __name__ == '__main__':
    sys.exit(main())
