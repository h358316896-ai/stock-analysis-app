"""简单的 XORPay HTTP 代理 - 运行在能访问 XORPay 的机器上"""
import http.server
import urllib.request
import urllib.parse
import json
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9876

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        try:
            content_len = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_len)

            req = urllib.request.Request('https://xorpay.com/api/pay/705874',
                data=body,
                headers={'Content-Type': 'application/x-www-form-urlencoded'})
            resp = urllib.request.urlopen(req, timeout=15)
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
            self.wfile.write(json.dumps({"status":"error","info":str(e)}).encode('utf-8'))

    def log_message(self, format, *args):
        print(f"[PROXY] {args[0]}" if args else "")

if __name__ == '__main__':
    server = http.server.HTTPServer(('0.0.0.0', PORT), ProxyHandler)
    print(f"XORPay proxy listening on port {PORT}")
    server.serve_forever()
