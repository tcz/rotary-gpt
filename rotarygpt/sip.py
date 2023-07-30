import logging
import re
import socket

class SIPServer:
    def __init__(self, bind_address, bind_port):
        self.bind_address = bind_address
        self.bind_port = bind_port
        self.socket = None
        self.shutdown_event = None

        self.incoming_call_callbacks = []
        self.call_ended_callbacks = []
        self.in_call = False

    def register_incoming_call_callback(self, callback):
        self.incoming_call_callbacks.append(callback)

    def register_call_ended_callback(self, callback):
        self.call_ended_callbacks.append(callback)

    def start(self, shutdown_event = None):
        self.shutdown_event = shutdown_event

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_address_sip = (self.bind_address, self.bind_port)
        self.socket.bind(server_address_sip)

        logging.info(f'SIP server started on {self.bind_address}:{self.bind_port}')

        while True:
            request = self._receive_request()
            if request is None:
                break

            logging.info(f'Incoming SIP request {request.method}')
            logging.debug(request.to_sip_message())

            self._handle_request(request)

        logging.info('SIP server stopped')

    def _receive_request(self):
        data = b''
        while not self.shutdown_event.is_set():
            try:
                self.socket.settimeout(0.2)
                chunk, address = self.socket.recvfrom(4096)
                self.socket.settimeout(None)
            except socket.timeout:
                continue

            data += chunk

            if b'\r\n\r\n' in data:
                header, body_so_far = data.split(b'\r\n\r\n', 1)
                request = SIPRequest(address)
                request.parse_request_header(header)

                if b'Content-Length' in request.headers:
                    chunk, _ = self.socket.recvfrom(int(request.headers[b'Content-Length']) - len(body_so_far))
                    request.body = body_so_far + chunk

                return request

        self.socket.close()
        self.socket = None

        return None

    def _handle_request(self, request):
        if request.method == b'INVITE':
            if self.in_call:
                return

            response = SipResponse(200, b"OK")
            response.headers[b'Via'] = request.headers[b'Via']
            response.headers[b'To'] = request.headers[b'To']
            response.headers[b'From'] = request.headers[b'From']
            response.headers[b'Contact'] = request.headers[b'To']
            response.headers[b'Call-ID'] = request.headers[b'Call-ID']
            response.headers[b'CSeq'] = request.headers[b'CSeq']
            response.headers[b'Content-type'] = b'application/sdp'

            to_host = self._extract_sip_host(request.headers[b'To'].decode('ascii')).encode('ascii')

            response.body = b"""v=0
o=RotaryGPT 1 1 IN IP4 """ + to_host + b"""
s=SIP Call
c=IN IP4 """ + to_host + b"""
t=0 0
m=audio 5004 RTP/AVP 0
a=sendrecv
a=rtpmap:0 PCMU/8000
a=ptime:20
""".replace(b"\n", b"\r\n")

            self.socket.sendto(response.to_sip_message(), request.from_address)
            self.in_call = True

            logging.info(f'SIP response sent {response.status_code}')
            logging.debug(response.to_sip_message())

            regex = r"audio (\d+) RTP"
            match = re.search(regex, request.body.decode('ascii'))

            if not match:
                return

            port = int(match.group(1))

            logging.debug(f'Calling incoming call callbacks with client RTP address {request.from_address[0]}:{port}')
            for callback in self.incoming_call_callbacks:
                callback(request.from_address[0], port)

        elif request.method == b'BYE':
            if not self.in_call:
                return

            self.in_call = False

            response = SipResponse(200, b"OK")
            response.headers[b'Via'] = request.headers[b'Via']
            response.headers[b'To'] = request.headers[b'To']
            response.headers[b'From'] = request.headers[b'From']
            response.headers[b'Contact'] = request.headers[b'To']
            response.headers[b'Call-ID'] = request.headers[b'Call-ID']
            response.headers[b'CSeq'] = request.headers[b'CSeq']

            self.socket.sendto(response.to_sip_message(), request.from_address)

            logging.info(f'SIP response sent {response.status_code}')
            logging.debug(response.to_sip_message())

            logging.debug(f'Calling call ended callbacks')
            for callback in self.call_ended_callbacks:
                callback()

    @staticmethod
    def _extract_sip_host(sip_address):
        sip_address = sip_address.strip('<> ')
        sip_uri_pattern = r"sip:(?P<host>[a-zA-Z0-9.-]+)"
        sip_uri_regex = re.compile(sip_uri_pattern)
        match = sip_uri_regex.search(sip_address)

        if match:
            return match.group("host")
        return None

class SIPRequest:
    def __init__(self, from_address):
        self.from_address = from_address
        self.method = None
        self.uri = None
        self.headers = {}
        self.body = None

    def parse_request_header(self, data):
        lines = data.split(b'\r\n')
        request_line = lines[0].split(b' ')
        self.method = request_line[0]
        self.uri = request_line[1]

        for line in lines[1:]:
            if line == '':
                break

            key, value = line.split(b':', 1)

            key = key.strip()
            value = value.strip()

            self.headers[key] = value

    def to_sip_message(self):
        message = self.method + b" " + self.uri + b" SIP/2.0\r\n"

        for header_key, header_value in self.headers.items():
            message += header_key + b": " + header_value + b"\r\n"

        message += b"\r\n"

        if self.body:
            message += self.body

        return message

class SipResponse:
    def __init__(self, status_code, status_message):
        self.status_code = status_code
        self.status_message = status_message
        self.headers = {}
        self.body = None

    def to_sip_message(self):
        message = b"SIP/2.0 " + str(self.status_code).encode('ascii') + b" " + self.status_message + b"\r\n"

        headers_to_send = self.headers.copy()

        if self.body:
            headers_to_send[b'Content-Length'] = str(len(self.body)).encode('ascii')
        else:
            headers_to_send[b'Content-Length'] = "0".encode('ascii')

        for header_key, header_value in headers_to_send.items():
            message += header_key + b": " + header_value + b"\r\n"

        message += b"\r\n"

        if self.body:
            message += self.body

        return message