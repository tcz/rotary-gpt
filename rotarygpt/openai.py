import socket
import ssl
import json
from datetime import datetime
import os

from rotarygpt.audio import wave_header

class WhisperRequest:
    def __init__(self, shutdown_event):
        self.shutdown_event = shutdown_event
        self.api_key = os.environ['OPENAI_API_KEY']

        self.socket = None
        self.target_host = "api.openai.com"
        self.target_port = 443
        self.is_accepting_audio = False

    def start_request(self):
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        context = ssl.create_default_context()

        self.socket = context.wrap_socket(client_socket, server_hostname=self.target_host)
        self.socket.connect((self.target_host, self.target_port))

        http_body = b"--112FEUERNOTRUF110\r\nContent-Disposition: form-data; name=\"model\"\r\n\r\nwhisper-1\r\n--112FEUERNOTRUF110\r\nContent-Disposition: form-data; name=\"file\"; filename=\"data.wav\"\r\n\r\n"
        http_body = http_body + wave_header()

        http_header = b"""POST /v1/audio/transcriptions HTTP/1.1
Host: """ + self.target_host.encode('ascii') + b"""
Authorization: Bearer """ + self.api_key.encode('ascii') + b"""
Transfer-Encoding: chunked
Connection: close
Content-Type: multipart/form-data; boundary=112FEUERNOTRUF110""".replace(b"\n", b"\r\n")

        http_chunk = '{:x}'.format(len(http_body)).encode('ascii') + b"\r\n" + http_body + b"\r\n"
        self.socket.sendall(http_header + b"\r\n\r\n" + http_chunk)

        self.is_accepting_audio = True

    def add_audio_chunk(self, chunk):
        if not self.is_accepting_audio:
            return

        http_chunk = '{:x}'.format(len(chunk)).encode('ascii') + b"\r\n" + chunk + b"\r\n"
        self.socket.sendall(http_chunk)

    def finish_request(self):
        if not self.is_accepting_audio:
            return
        self.is_accepting_audio = False

        closing_boundary = b'\r\n--112FEUERNOTRUF110--\r\n'
        http_chunk = '{:x}'.format(len(closing_boundary)).encode('ascii') + b"\r\n" + closing_boundary + b"\r\n"
        http_chunk = http_chunk + b"0\r\n\r\n"
        self.socket.sendall(http_chunk)


    def discard_request(self):
        self.is_accepting_audio = False
        if self.socket is not None:
            self.socket.close()
            self.socket = None

    def get_response(self):
        if self.socket is None:
            return

        response = b""
        while not self.shutdown_event.is_set():
            data = self.socket.recv(1024)
            if not data:
                break
            response += data

        if self.shutdown_event.is_set():
            return None

        body = response.split(b'\r\n\r\n', 1)[1]
        parsed_body = json.loads(body)
        text = parsed_body['text'] if 'text' in parsed_body else None

        self.socket.close()
        self.socket = None

        return text


class GPTRequest:
    def __init__(self, shutdown_event):
        self.shutdown_event = shutdown_event
        self.api_key = os.environ['OPENAI_API_KEY']
        self.physical_location = os.environ['ROTARYGPT_PHYSICAL_LOCATION']

        self.socket = None
        self.target_host = "api.openai.com"
        self.target_port = 443

    def send_request(self, function_definitions, conversation_items):
        conversation_items = [{
            "role": "system",
            "content": "You are a phone agent living in an old rotary phone, acting as a smart home assistant. " + \
                       "Keep your responses short and casual. Oh, you have a German accent. Today's date is " + \
                       datetime.utcnow().strftime('%Y-%m-%d, %A') + ". You are physically located in " + \
                       self.physical_location + ".",
        }] + conversation_items

        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        context = ssl.create_default_context()

        self.socket = context.wrap_socket(client_socket, server_hostname=self.target_host)
        self.socket.connect((self.target_host, self.target_port))

        http_body = json.dumps({
            "model": "gpt-3.5-turbo-0613",
            "messages": conversation_items,
            "functions": function_definitions
        }).encode('utf-8')

        http_header = b"""POST /v1/chat/completions HTTP/1.1
Host: """ + self.target_host.encode('ascii') + b"""
Authorization: Bearer """ + self.api_key.encode('ascii') + b"""
Content-Type: application/json
Content-Length: """ + str(len(http_body)).encode('ascii') + b"""
Connection: close""".replace(b"\n", b"\r\n")

        self.socket.sendall(http_header + b"\r\n\r\n" + http_body)

    def get_response(self):
        response = b""
        while not self.shutdown_event.is_set():
            data = self.socket.recv(1024)
            if not data:
                break
            response += data

        if self.shutdown_event.is_set():
            return None

        header, body = response.split(b'\r\n\r\n', 1)
        if b'Transfer-Encoding: chunked' in header:
            body = self._unchunk_body(body)

        parsed_body = json.loads(body.decode('utf-8'))
        text = parsed_body['choices'][0]['message'] if 'choices' in parsed_body else None

        self.socket.close()
        self.socket = None

        return text

    def _unchunk_body(self, body):
        unchunked_body = b''
        while True:
            chunk_size, rest = body.split(b"\r\n", 1)
            chunk_size = int(chunk_size, 16)

            if 0 == chunk_size:
                break

            chunk, body = rest[:chunk_size], rest[chunk_size + 2:]
            unchunked_body += chunk

        return unchunked_body
