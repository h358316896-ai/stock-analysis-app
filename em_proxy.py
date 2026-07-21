"""Eastmoney API Proxy — 运行在阿里云ECS上，绕过geo-blocking"""
import http.server
import urllib.request
import urllib.parse
import json
import sys
import ssl

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8444

class EMProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            raw = params.get('url', [None])[0]
            if not raw:
                self.send_error(400, "Missing 'url' parameter")
                return
            target_url = urllib.parse.unquote(raw)  # 解码调用方 URL-encode 过的目标 URL

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://data.eastmoney.com/',
            }
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(target_url, headers=headers)
            resp = urllib.request.urlopen(req, timeout=15, context=ctx)
            data = resp.read()

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_response(502)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

    def log_message(self, format, *args):
        print(f"[EM-PROXY] {args[0]}" if args else "")

if __name__ == '__main__':
    server = http.server.HTTPServer(('0.0.0.0', PORT), EMProxyHandler)
    print(f"Eastmoney proxy listening on port {PORT}")
    server.serve_forever()
