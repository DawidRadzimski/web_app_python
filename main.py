import json
import mimetypes
import socket
import urllib.parse
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from http import HTTPStatus
from pathlib import Path
from threading import Thread

""" Define constants for socket configuration """
SOCKET_IP = "127.0.0.1"
SOCKET_PORT = 5000
STORAGE_PATH = Path("storage")

""" Define HTTP request handler class """


class HttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == '/':
            self.send_html_file(Path('./index.html'))
        elif pr_url.path == '/message':
            self.send_html_file(Path('./message.html'))
        else:
            if Path(pr_url.path[1:]).exists():
                self.send_static()
            else:
                self.send_html_file(Path('./error.html'), 404)

    """ Handle POST requests """

    def do_POST(self):
        if self.path == '/message':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            parsed_data = urllib.parse.parse_qs(post_data)
            username = parsed_data['username'][0]
            message = parsed_data['message'][0]
            current_time = datetime.now().isoformat()

            try:
                udp_socket.sendto(json.dumps({current_time: {"username": username, "message": message}}).encode(),
                                  (SOCKET_IP, SOCKET_PORT))
            except Exception as e:
                print("Error sending data via UDP:", e)

            self.send_response(HTTPStatus.FOUND.value)
            self.send_header('Location', '/')
            self.end_headers()
        else:
            self.send_response(HTTPStatus.NOT_FOUND.value)
            self.end_headers()

    """ Send an HTML file as response """

    def send_html_file(self, filename, status=HTTPStatus.OK.value):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

    """ Send a static file as response """

    def send_static(self):
        file_path = f'.{self.path}'
        self.send_response(HTTPStatus.OK.value)
        mt = mimetypes.guess_type(file_path)
        if mt:
            self.send_header('Content-type', mt[0])
        else:
            self.send_header('Content-type', 'text/plain')
        self.end_headers()
        with open(file_path, 'rb') as file:
            self.wfile.write(file.read())


""" Run the HTTP server """


def run_http_server(server_class=HTTPServer, handler_class=HttpHandler):
    server_address = ('', 3000)
    http = server_class(server_address, handler_class)
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        http.server_close()


""" Save data to a JSON file """


def save_data(data):
    data_parse = urllib.parse.unquote_plus(data.decode())
    data_path = STORAGE_PATH.joinpath("data.json")
    try:
        with open(data_path, encoding="utf-8") as file:
            data_json = json.load(file)
    except FileNotFoundError:
        data_json = {}
    data_json[str(datetime.now())] = {key: value for key, value in [
        el.split('=') for el in data_parse.split('&')]}
    with open(data_path, "w", encoding="utf-8") as fh:
        json.dump(data_json, fh, indent=4, ensure_ascii=False)


""" Run the UDP socket server """


def run_udp_socket_server(ip, port):
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server = ip, port
    udp_socket.bind(server)
    try:
        while True:
            data, address = udp_socket.recvfrom(1024)
            save_data(data)

    except KeyboardInterrupt:
        print(f'Keyboard interrupt detected. Shutting down the server.')
    finally:
        udp_socket.close()


""" Main function """
if __name__ == '__main__':
    print('The server has been successfully started!')
    if not STORAGE_PATH.exists():
        STORAGE_PATH.mkdir()

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket_server_thread = Thread(
        target=run_udp_socket_server, args=(SOCKET_IP, SOCKET_PORT))
    udp_socket_server_thread.start()

    run_http_server()
