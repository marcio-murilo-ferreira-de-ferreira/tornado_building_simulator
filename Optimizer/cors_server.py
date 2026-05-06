import http.server
import socketserver
import json
import os
import sys

PORT = 4175

class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        return super(CORSRequestHandler, self).end_headers()

    def do_GET(self):
        if self.path == '/data.json':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            try:
                with open('retrofit_dashboard_data.json', 'r', encoding='utf-8') as f:
                    self.wfile.write(f.read().encode('utf-8'))
            except Exception as e:
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            return
            
        elif self.path == '/manifest.json':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            try:
                with open('fe_images_manifest.json', 'r', encoding='utf-8') as f:
                    self.wfile.write(f.read().encode('utf-8'))
            except Exception as e:
                 self.wfile.write(b"{}")
            return
            
        return super(CORSRequestHandler, self).do_GET()

if __name__ == '__main__':
    with socketserver.TCPServer(("", PORT), CORSRequestHandler) as httpd:
        print(f"CORS Server running on port {PORT}...")
        httpd.serve_forever()
