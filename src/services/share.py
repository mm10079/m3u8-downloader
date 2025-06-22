from http.server import SimpleHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import threading
import socket

httpd_server = None

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """允許多發連線的 HTTPServer"""
    daemon_threads = True  # 確保線程在主程序退出時終止

class MyHTTPRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # 覆寫此方法以禁用日誌輸出
        pass
    
    def end_headers(self):
        self.send_header('Content-Disposition', 'attachment')
        SimpleHTTPRequestHandler.end_headers(self)

def run(server_class=ThreadedHTTPServer, handler_class=MyHTTPRequestHandler, directory='.'):
    global httpd_server
    server_address = ('', port)
    httpd_server = server_class(server_address, lambda *args, **kwargs: handler_class(*args, directory=directory, **kwargs))
    print(f"Server started on port {port}, serving directory: {directory}")
    httpd_server.serve_forever()

def stop():
    # 關閉伺服器
    if httpd_server:
        httpd_server.shutdown()
        httpd_server.server_close()

def get_local_ip() -> str | None:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
        print(f"啟動檔案伺服器，網址: \"http://{local_ip}:{port}\"")
        return f"http://{local_ip}:{port}/"
    except Exception as e:
        print("Error:", e)
        return None

def main(set_port=8000, directory='.') -> str:
    global port
    port = set_port
    url = get_local_ip()
    t = threading.Thread(target=run, args=(ThreadedHTTPServer, MyHTTPRequestHandler, directory), daemon=True)
    t.start()
    if url:
        return url
    else:
        raise Exception("無法獲取本地 IP 地址")
    

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="啟動簡易 HTTP 檔案伺服器")
    parser.add_argument('--port', type=int, default=8000, help="指定伺服器埠號 (預設: 8000)")
    parser.add_argument('--directory', type=str, default='.', help="指定伺服器根目錄 (預設: 當前目錄)")
    args = parser.parse_args()

    port = args.port
    directory = args.directory
    get_local_ip()
    run(directory=directory)
