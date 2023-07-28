import binascii
import logging
import queue
import socket
import random
import time

from rotarygpt.audio import wave_header


class RTPReceiver:

    def __init__(self, bind_address, bind_port, audio_chunk_queue):
        self.bind_address = bind_address
        self.bind_port = bind_port
        self.audio_chunk_queue = audio_chunk_queue
        self.socket = None
        self.shutdown_event = None

    def start(self, shutdown_event = None):
        self.shutdown_event = shutdown_event

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_address_rtp = (self.bind_address, self.bind_port)
        self.socket.bind(server_address_rtp)

        logging.info(f'RTP receiver started on {self.bind_address}:{self.bind_port}')

        self._receive_audio()

        self.socket.close()
        self.socket = None

        logging.info(f'RTP receiver stopped')

    def _receive_audio(self):
        self.socket.settimeout(0.2)
        while not self.shutdown_event.is_set():
            try:
                chunk, address = self.socket.recvfrom(160 + 12)  # 20ms is 160 8bit samples plus header
            except socket.timeout:
                continue

            self.audio_chunk_queue.put(chunk[12:])


class RTPSender:

    def __init__(self, connect_address, connect_port, audio_chunk_queue):
        self.connect_address = connect_address
        self.connect_port = connect_port
        self.audio_chunk_queue = audio_chunk_queue
        self.socket = None
        self.shutdown_event = None
        self.sequence_number = random.randint(0, 255)
        self.timer = random.randint(0, 255)
        self.synchronization_source = random.randint(0, 4294967295)

        self.file = open('/tmp/conversation.wav', 'wb')
        self.file.write(wave_header())
        self.marker_bit = True

    def start(self, shutdown_event = None):
        self.shutdown_event = shutdown_event
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        logging.info(f'RTP sender started with peer {self.connect_address}:{self.connect_port}')

        self._send_audio()

        self.socket.close()
        self.socket = None

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

                self.socket.sendto(header + chunk[0:160], (self.connect_address, self.connect_port))
                self.file.write(chunk[0:160])

                chunk = chunk[160:]
                self.sequence_number += 1
                self.timer += 160 # timer is incremented by the sample number, on out case 160 samples per packet (8 bit pcmu)
                self.marker_bit = False

                sleep_time = 0.02 - (time.perf_counter() - start_time)
                accurate_sleep(max(0.0, sleep_time))
                # Correcting in case the sleep time was negative
                start_time = time.perf_counter() + min(sleep_time, 0.0)

def accurate_sleep(duration):
    now = time.perf_counter()
    end = now + duration
    while now < end:
        now = time.perf_counter()