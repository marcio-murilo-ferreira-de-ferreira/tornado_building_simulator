import http.server
import socketserver
import os

dist_dir = os.path.join(os.path.dirname(__file__), 'tornado-control-center', 'dist')
os.chdir(dist_dir)

PORT = 4179

class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        super().end_headers()

class ThreadingSimpleServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

if __name__ == '__main__':
    with ThreadingSimpleServer(("", PORT), NoCacheHandler) as httpd:
        print(f"React Production UI Server running multi-threaded on port {PORT}...")
        httpd.serve_forever()
