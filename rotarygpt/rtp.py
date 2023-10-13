import binascii
import logging
import queue
import socket
import random
import time

from rotarygpt.audio import wave_header


class RTPReceiver:

    def __init__(self, shared_socket, audio_chunk_queue):
        self.audio_chunk_queue = audio_chunk_queue
        self.shared_socket = shared_socket
        self.shutdown_event = None

    def start(self, shutdown_event = None):
        self.shutdown_event = shutdown_event

        bind_address, bind_port = self.shared_socket.getsockname()
        logging.info(f'RTP receiver started on {bind_address}:{bind_port}')

        self._receive_audio()

        self.shared_socket.close()

        logging.info(f'RTP receiver stopped')

    def _receive_audio(self):
        self.shared_socket.settimeout(0.2)
        while not self.shutdown_event.is_set():
            try:
                chunk, address = self.shared_socket.recvfrom(160 + 12)  # 20ms is 160 8bit samples plus header
            except socket.timeout:
                continue

            self.audio_chunk_queue.put(chunk[12:])


class RTPSender:

    def __init__(self, shared_socket, connect_address, connect_port, audio_chunk_queue):
        self.connect_address = connect_address
        self.connect_port = connect_port
        self.audio_chunk_queue = audio_chunk_queue
        self.shared_socket = shared_socket
        self.shutdown_event = None
        self.sequence_number = random.randint(0, 255)
        self.timer = random.randint(0, 255)
        self.synchronization_source = random.randint(0, 4294967295)

        self.file = open('/tmp/conversation.wav', 'wb')
        self.file.write(wave_header())
        self.marker_bit = True

    def start(self, shutdown_event = None):
        self.shutdown_event = shutdown_event

        logging.info(f'RTP sender started with peer {self.connect_address}:{self.connect_port}')

        self._send_audio()

        self.shared_socket.close()

        self.file.close()
        self.file = None

        logging.info(f'RTP sender stopped')

    def _send_audio(self):
        chunk = b''
        start_time = None
        while not self.shutdown_event.is_set():
            try:
                chunk += self.audio_chunk_queue.get(block=False)
            except queue.Empty:
                continue

            # New talkspurt
            if start_time is None or time.perf_counter() - start_time > 1.0:
                logging.debug(f'New talkspurt, marker bit set')
                start_time = time.perf_counter()
                self.marker_bit = True

            while len(chunk) >= 160:
                # https://datatracker.ietf.org/doc/html/rfc3550#section-5.1
                header = b'\x80\x80' if self.marker_bit else b'\x80\x00'
                header += self.sequence_number.to_bytes(2, 'big', signed=False)
                header += self.timer.to_bytes(4, 'big', signed=False)
                header += self.synchronization_source.to_bytes(4, 'big', signed=False)

                self.shared_socket.sendto(header + chunk[0:160], (self.connect_address, self.connect_port))
                self.file.write(chunk[0:160])

                chunk = chunk[160:]
                self.sequence_number += 1
                self.timer += 160 # timer is incremented by the sample number, on out case 160 samples per packet (8 bit pcmu)
                self.marker_bit = False

                sleep_time = 0.02 - (time.perf_counter() - start_time)
                accurate_sleep(max(0.0, sleep_time))
                # Correcting in case the sleep time was negative
                start_time = time.perf_counter() + min(sleep_time, 0.0)

class SharedSocket:
    def __init__(self):
        self.socket = None

    def bind(self, bind_address, bind_port):
        if self.socket is not None:
            return self.socket

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((bind_address, bind_port))

        return self.socket

    def settimeout(self, timeout):
        if self.socket is not None:
            self.socket.settimeout(timeout)

    def recvfrom(self, size):
        if self.socket is not None:
            return self.socket.recvfrom(size)

    def sendto(self, data, address):
        if self.socket is not None:
            self.socket.sendto(data, address)

    def getsockname(self):
        if self.socket is not None:
            return self.socket.getsockname()

    def close(self):
        if self.socket is not None:
            self.socket.close()
            self.socket = None

def accurate_sleep(duration):
    now = time.perf_counter()
    end = now + duration
    while now < end:
        now = time.perf_counter()