import os
import socket
import ssl
import json
from hashlib import sha256
import hmac
import datetime

class PollyRequest:
    def __init__(self, chunk_callback, shutdown_event):
        self.chunk_callback = chunk_callback
        self.shutdown_event = shutdown_event

        self.socket = None
        self.target_host = "polly.eu-west-1.amazonaws.com"
        self.target_port = 443

        self.aws_key = os.environ['AWS_ACCESS_KEY']
        self.aws_secret = os.environ['AWS_SECRET_KEY']

    def send_request(self, text):
        parameters = {
          "VoiceId": "Daniel",
          "OutputFormat": "pcm",
          "Text": text,
          "Engine": "neural",
          "SampleRate": "8000"
        }

        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        context = ssl.create_default_context()

        self.socket = context.wrap_socket(client_socket, server_hostname=self.target_host)
        self.socket.connect((self.target_host, self.target_port))

        http_body = json.dumps(parameters).encode('utf-8')
        timestamp = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ').encode('ascii')
        signature = self._get_signature(timestamp, http_body)

        authorization = b"""AWS4-HMAC-SHA256 Credential=""" + self.aws_key.encode('ascii') +  b"/" + timestamp[:8] + \
                        b"/eu-west-1/polly/aws4_request, SignedHeaders=content-type;host;x-amz-date, Signature=" + \
                        signature.encode('ascii')

        http_header = b"""POST /v1/speech HTTP/1.1
Host: """ + self.target_host.encode('ascii') + b"""
Content-Type: application/json
Content-Length: """ + str(len(http_body)).encode('ascii') + b"""
X-Amz-Date: """ + timestamp + b"""
Authorization: """ + authorization + b"""
Connection: close""".replace(b"\n", b"\r\n")

        self.socket.sendall(http_header + b"\r\n\r\n" + http_body)

    def get_response(self):
        response = b""
        body = b""

        while not self.shutdown_event.is_set():
            chunk = self.socket.recv(1024)
            response += chunk

            if b'\r\n\r\n' in response:
                header, body = response.split(b'\r\n\r\n', 1)
                print(header)
                break

        while not self.shutdown_event.is_set():
            while b"\r\n" not in body and not self.shutdown_event.is_set():
                body += self.socket.recv(1024)

            if self.shutdown_event.is_set():
                break

            chunk_size, chunk = body.split(b"\r\n", 1)
            chunk_size = int(chunk_size, 16)

            if 0 == chunk_size:
                break

            while len(chunk) < chunk_size + 2:
                chunk += self.socket.recv(1024)

            chunk, body = chunk[:chunk_size], chunk[chunk_size + 2:]

            self.chunk_callback(chunk)


    def _get_signature(self, timestamp, http_body):
        # This is the most convoluted way to sign a request I've ever seen
        canonical_request = self._get_canonical_request(timestamp, http_body)

        request_hash = sha256(canonical_request).hexdigest().encode('ascii')

        string_to_sign = b"AWS4-HMAC-SHA256\n" + timestamp + b"\n" + timestamp[:8] + b"/eu-west-1/polly/aws4_request\n" + request_hash

        digest = hmac.new(("AWS4" + self.aws_secret).encode(), timestamp[0:8], sha256).digest()
        digest = hmac.new(digest, b'eu-west-1', sha256).digest()
        digest = hmac.new(digest, b'polly', sha256).digest()
        digest = hmac.new(digest, b'aws4_request', sha256).digest()

        return hmac.new(digest, string_to_sign, sha256).hexdigest()


    def _get_canonical_request(self, timestamp, http_body):
        payload_hash = sha256(http_body).hexdigest()
        return b"""POST
/v1/speech

content-type:application/json
host:""" + self.target_host.encode('ascii') + b"""
x-amz-date:""" + timestamp + b"""

content-type;host;x-amz-date
""" + payload_hash.encode('ascii')


