import json
import logging
import threading
import time

from rotarygpt.audio import PCMUSilenceDetector, linear_to_mu_law_sample
from rotarygpt.aws import PollyRequest
from rotarygpt.openai import WhisperRequest, GPTRequest
from rotarygpt.utils import clear_queue


class Conversation:
    def __init__(self, audio_chunk_queue_in, audio_chunk_queue_out, function_manager):
        self.audio_chunk_queue_in = audio_chunk_queue_in
        self.audio_chunk_queue_out = audio_chunk_queue_out
        self.function_manager = function_manager

        self.conversation_items = []
        self.current_whisper_request = None
        self.silence_detector = PCMUSilenceDetector()
        self.shutdown_event = None
        self.response_arrived_event = threading.Event()

    def start(self, shutdown_event = None):
        logging.info("Conversation started")
        self.shutdown_event = shutdown_event
        PollyRequest.voice = PollyRequest.default_voice

        try:
            self._greet()

            while not self.shutdown_event.is_set():
                self._start_whisper_request()
                self._receive_audio()
                if self.shutdown_event.is_set():
                    break

                logging.debug("Silence detected")

                self._start_wait_speaker()
                self._finish_current_whisper_request()

                agent_text = None
                while agent_text is None and not self.shutdown_event.is_set():
                    agent_text = self._send_gpt_request()
                    if self.shutdown_event.is_set():
                        break

                if self.shutdown_event.is_set():
                    break

                self._send_polly_request(agent_text)

                logging.debug("Polly fully returned, waiting for audio out queue to be consumed")

                while not self.audio_chunk_queue_out.empty() and not self.shutdown_event.is_set():
                    # Wait until the speech is finished, otherwise the Whisper request times out.
                    pass

                logging.debug("Audio out queue empty")

                clear_queue(self.audio_chunk_queue_in)
                self.silence_detector.reset_had_signal()

        except:
            logging.exception('Exception during the conversation')
            self._send_error_message()
        finally:
            self.response_arrived_event.set()
            self._discard_current_whisper_request()
            logging.info("Conversation ended")

    def on_polly_chunk(self, chunk):
        self.response_arrived_event.set()

        logging.debug("Polly chunk arrived, sending to RTP")
        converted_chunk = b''
        for i in range(0, len(chunk), 2):
            sample = int.from_bytes(chunk[i:i+2], 'little', signed=True)
            mu_sample = linear_to_mu_law_sample(sample)
            converted_chunk += mu_sample.to_bytes(1, 'little')

        self.audio_chunk_queue_out.put(converted_chunk)

    def _receive_audio(self):
        logging.debug("Receiving audio")
        while not self.shutdown_event.is_set():
            chunk = self.audio_chunk_queue_in.get()

            if self.current_whisper_request is not None and self.audio_chunk_queue_out.empty():
                self.current_whisper_request.add_audio_chunk(chunk)
                if self.silence_detector.add_sample_and_detect_silence(chunk):
                    break

    def _finish_current_whisper_request(self):
        logging.debug("Sending Whisper request")
        self.current_whisper_request.finish_request()
        text = self.current_whisper_request.get_response()

        logging.debug("Whisper returned")

        self.current_whisper_request = None
        if text is not None and text != "":
            self.conversation_items.append(
                {"role": "user", "content": text}
            )
            logging.info("User message: \x1b[31;1m" + text + "\x1b[0m")

    def _discard_current_whisper_request(self):
        if self.current_whisper_request is None:
            return
        logging.debug("Discarding Whisper request")
        self.current_whisper_request.discard_request()

    def _start_whisper_request(self):
        logging.debug("Starting Whisper request")
        self.current_whisper_request = WhisperRequest(self.shutdown_event)
        self.current_whisper_request.start_request()

    def _send_gpt_request(self):
        logging.debug("Sending GPT request")
        gpt_request = GPTRequest(self.shutdown_event)
        gpt_request.send_request(self.function_manager.available_functions(), self.conversation_items)
        message = gpt_request.get_response()

        if message is None:
            return None

        self.conversation_items.append(
            message
        )

        if 'function_call' in message:
            logging.info('Function call: ' + str(message))

            function_response = self.function_manager.call(
                message['function_call']['name'],
                json.loads(message['function_call']['arguments'])
            )
            self.conversation_items.append(
                {"role": "function", "content": function_response, "name": message['function_call']['name']}
            )
            return None

        logging.info("Agent message: \x1b[33;1m" + message['content'] + "\x1b[0m")

        return message['content']

    def _send_polly_request(self, text):
        logging.debug("Sending Polly request")
        polly_request = PollyRequest(self.on_polly_chunk, self.shutdown_event)
        polly_request.send_request(text)
        polly_request.get_response()

    def _greet(self):
        logging.debug("Sending greeting")
        self._play_pcm("audio/greeting.pcm")
        self.conversation_items.append(
            {"role": "assistant", "content": "Hallo. How can I help?"}
        )

    def _send_error_message(self):
        logging.debug("Sending error message")
        self._play_pcm("audio/error-message.pcm")

    def _start_wait_speaker(self):
        self.response_arrived_event.clear()
        thread = threading.Thread(target=self._speak_if_waiting_too_long, daemon=True, name='Wait speaker')
        thread.start()

    def _speak_if_waiting_too_long(self):
        wait_time = 4.0
        time.sleep(wait_time)
        if self.response_arrived_event.is_set():
            return

        logging.info(f"Waited longer than {wait_time}s to respond, sending wait a moment")
        self._play_pcm("audio/one-second.pcm")
        self.conversation_items.append(
            {"role": "assistant", "content": "One second, bitte."}
        )

    def _play_pcm(self, file_path):
        converted_chunk = b''
        with open(file_path, 'rb') as file:
            while not self.shutdown_event.is_set():
                chunk = file.read(2)
                if chunk == b"":
                    break

                sample = int.from_bytes(chunk, 'little', signed=True)
                mu_sample = linear_to_mu_law_sample(sample)
                converted_chunk += mu_sample.to_bytes(1, 'little')

        self.audio_chunk_queue_out.put(converted_chunk)

    def _germanize(self, text):
        return text.\
            replace('the', 'ze').\
            replace('The', 'Ze')

