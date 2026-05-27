"""Daily News Globe — local HTTP server.

Run:  python server.py
Open: http://localhost:8765/

After the cloud migration, this server is optional. Kept for local dev / preview.
The actual data refresh is done in cloud (.github/workflows/daily.yml).
"""
import logging
import os
import socket
import sys
import threading
import time
import traceback
from http.server import HTTPServer, SimpleHTTPRequestHandler
from logging.handlers import RotatingFileHandler

from fetcher import COUNTRIES, CATEGORIES, fetch_all

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PORT = 8765
HOST = '0.0.0.0'
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(PROJECT_DIR, 'server.log')
REFRESH_INTERVAL_SECONDS = 6 * 3600

_log_fmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
_logger = logging.getLogger('globe-news')
_logger.setLevel(logging.INFO)
_fh = RotatingFileHandler(LOG_FILE, maxBytes=512_000, backupCount=2, encoding='utf-8')
_fh.setFormatter(_log_fmt)
_logger.addHandler(_fh)
_sh = logging.StreamHandler()
_sh.setFormatter(_log_fmt)
_logger.addHandler(_sh)


def log(msg):
    _logger.info(msg)


def get_lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.254.254.254', 1))
        return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'
    finally:
        s.close()


def scheduler_loop():
    while True:
        try:
            fetch_all()
        except Exception:
            log('fetch_all crashed:\n' + traceback.format_exc())
        time.sleep(REFRESH_INTERVAL_SECONDS)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PROJECT_DIR, **kwargs)

    def log_message(self, fmt, *args):
        if args and len(args) >= 2 and str(args[1])[:1] in ('4', '5'):
            super().log_message(fmt, *args)

    def end_headers(self):
        if self.path.endswith('news-data.json'):
            self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def do_GET(self):
        if self.path == '/refresh':
            threading.Thread(target=fetch_all, daemon=True).start()
            body = b'{"status":"refresh started"}'
            self.send_response(202)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()


def main():
    lan_ip = get_lan_ip()
    log(f'Daily News Globe starting on {HOST}:{PORT}')
    log(f'  Local:  http://localhost:{PORT}/')
    log(f'  LAN:    http://{lan_ip}:{PORT}/  (use this on phone/tablet)')
    log(f'  Static: {PROJECT_DIR}')
    log(f'  Coverage: {len(COUNTRIES)} countries x {len(CATEGORIES)} categories')
    log(f'  Refresh: every {REFRESH_INTERVAL_SECONDS // 3600}h, manual via GET /refresh')
    threading.Thread(target=scheduler_loop, daemon=True).start()
    try:
        HTTPServer((HOST, PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        log('Stopped by keyboard interrupt.')


if __name__ == '__main__':
    main()
