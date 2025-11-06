import http.server
import socketserver
import os
from pathlib import Path

# Переход в корневую директорию проекта
BASE_DIR = Path(__file__).parent
os.chdir(BASE_DIR)

PORT = 8080

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def _proxy_to_backend(self, method: str, strip_api_prefix=True):
        # Forward requests to backend http://localhost:8000/*
        import http.client
        import urllib.parse
        import socket

        backend_host = "localhost"
        backend_port = 8000

        # Strip /api prefix only if requested (for /api/* requests)
        if strip_api_prefix and self.path.startswith('/api'):
            target_path = self.path[len("/api"):]
            if not target_path:
                target_path = "/"
        else:
            # For /uploads/ and other paths, use the path as-is
            target_path = self.path

        # Read body (if any)
        content_length = int(self.headers.get('Content-Length', 0) or 0)
        body = self.rfile.read(content_length) if content_length > 0 else None

        # Build and send request to backend
        conn = http.client.HTTPConnection(backend_host, backend_port, timeout=30)
        try:
            # Forward headers, excluding hop-by-hop
            forward_headers = {k: v for k, v in self.headers.items() if k.lower() not in {
                'host', 'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
                'te', 'trailers', 'transfer-encoding', 'upgrade',
                # Kaspersky injected headers sometimes break CORS
                'origin'
            }}

            conn.request(method, target_path, body=body, headers=forward_headers)
            resp = conn.getresponse()
            data = resp.read()

            # Write response back to client
            self.send_response(resp.status, resp.reason)
            # Pass through headers except hop-by-hop
            for header, value in resp.getheaders():
                if header.lower() in {
                    'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
                    'te', 'trailers', 'transfer-encoding', 'upgrade', 'content-encoding'
                }:
                    continue
                self.send_header(header, value)
            # Ensure CORS and content-type are present
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', '*')
            self.end_headers()
            self.wfile.write(data)
        except (ConnectionRefusedError, TimeoutError, socket.gaierror, socket.timeout, http.client.HTTPException, OSError) as e:
            # Backend unavailable or failed — return 502 instead of closing connection
            message = f"Backend http://{backend_host}:{backend_port} unavailable: {e}"
            self.send_response(502, "Bad Gateway")
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', '*')
            self.end_headers()
            self.wfile.write(("{""error"": ""Bad Gateway"", ""detail"": ""%s""}" % message).encode('utf-8'))
        finally:
            conn.close()

    def do_OPTIONS(self):
        if self.path.startswith('/api/') or self.path == '/api' or self.path == '/api/':
            # Handle CORS preflight at proxy layer
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', '*')
            self.end_headers()
            return
        return super().do_OPTIONS()

    def do_GET(self):
        if self.path.startswith('/api/') or self.path == '/api' or self.path == '/api/':
            return self._proxy_to_backend('GET')
        # Проксируем запросы к /uploads/ на бэкенд
        if self.path.startswith('/uploads/'):
            return self._proxy_to_backend('GET', strip_api_prefix=False)
        # Явный редирект с корня на главную страницу index.html
        if self.path == "/" or self.path == "/index.html":
            self.send_response(302)
            self.send_header("Location", "/frontend/templates/index.html")
            self.end_headers()
            return
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith('/api/') or self.path == '/api' or self.path == '/api/':
            return self._proxy_to_backend('POST')
        return super().do_POST()

    def do_PUT(self):
        if self.path.startswith('/api/') or self.path == '/api' or self.path == '/api/':
            return self._proxy_to_backend('PUT')
        return super().do_PUT()

    def do_PATCH(self):
        if self.path.startswith('/api/') or self.path == '/api' or self.path == '/api/':
            return self._proxy_to_backend('PATCH')
        return super().do_PATCH()

    def do_DELETE(self):
        if self.path.startswith('/api/') or self.path == '/api' or self.path == '/api/':
            return self._proxy_to_backend('DELETE')
        return super().do_DELETE()

    def translate_path(self, path):
        # Перенаправляем короткие пути на фактические директории фронтенда
        if path == "/" or path == "/index.html":
            path = "/frontend/templates/index.html"
        elif path.startswith("/templates/"):
            path = "/frontend" + path
        elif path.startswith("/static/"):
            path = "/frontend" + path
        elif path == "/favicon.ico":
            # Отдаем логотип вместо фавиконки, чтобы не было 404
            path = "/images/logo.PNG"

        return super().translate_path(path)

    def end_headers(self):
        # Добавляем CORS заголовки
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        
        # Добавляем правильный Content-Type для UTF-8
        if self.path.endswith('.html'):
            self.send_header('Content-Type', 'text/html; charset=utf-8')
        elif self.path.endswith('.js'):
            self.send_header('Content-Type', 'application/javascript; charset=utf-8')
        elif self.path.endswith('.css'):
            self.send_header('Content-Type', 'text/css; charset=utf-8')
        
        super().end_headers()

    def log_message(self, format, *args):
        """Переопределяем логирование для более красивого вывода"""
        message = format % args
        print(f"📄 {message}")

def start_server():
    """Запуск HTTP сервера"""
    print("=" * 60)
    print("🚀 Запуск Frontend сервера")
    print("=" * 60)
    print(f"📂 Рабочая директория: {BASE_DIR}")
    print(f"🌐 URL: http://localhost:{PORT}")
    print(f"📄 Главная страница: http://localhost:{PORT}/")
    print(f"   Альтернативно:     http://localhost:{PORT}/frontend/templates/index.html")
    print("=" * 60)
    print("⚠️  Не закрывайте это окно!")
    print("✅ Нажмите Ctrl+C для остановки сервера")
    print("=" * 60)
    print()

    try:
        with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n🛑 Сервер остановлен пользователем")
    except OSError as e:
        if e.errno == 98:  # Address already in use
            print(f"\n❌ ОШИБКА: Порт {PORT} уже занят!")
            print(f"💡 Попробуйте:")
            print(f"   1. Закрыть другое приложение на порту {PORT}")
            print(f"   2. Запустить: python start_server.py --port 8081")
        else:
            raise

if __name__ == "__main__":
    import sys
    
    # Проверка аргументов для выбора порта
    if len(sys.argv) > 1 and sys.argv[1] == '--port' and len(sys.argv) > 2:
        PORT = int(sys.argv[2])
    
    start_server()

