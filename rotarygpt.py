import importlib
import os
import queue
import threading, sys
import time
from functools import partial
import logging

from rotarygpt.conversation import Conversation
from rotarygpt.rtp import RTPReceiver, RTPSender, SharedSocket
from rotarygpt.sip import SIPServer
from rotarygpt.functions import FunctionManager
from rotarygpt.utils import clear_queue

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s %(threadName)s [%(levelname)s]: %(message)s", datefmt='%Y-%m-%d %H:%M:%S')

# Low context switching interval needed for timely voice packet relay
sys.setswitchinterval(0.001)

def reset_event(event, *_):
    event.clear()

def start_rpt(threads, shutdown_event, audio_queue_in, audio_queue_out, ip, port):
    shared_socket = SharedSocket()
    shared_socket.bind('0.0.0.0', 5004)

    rtp_receiver = RTPReceiver(shared_socket, audio_queue_in)
    threads['rtp_receiver'] = threading.Thread(target=rtp_receiver.start, args=(shutdown_event,), daemon=True,
                                               name="RTP receiver")
    threads['rtp_receiver'].start()

    rtp_sender = RTPSender(shared_socket, ip, port, audio_queue_out)
    threads['rtp_sender'] = threading.Thread(target=rtp_sender.start, args=(shutdown_event,), daemon=True,
                                             name="RTP sender")
    threads['rtp_sender'].start()

def start_conversation(threads, shutdown_event, audio_queue_in, audio_queue_out, function_manager, *_):
    conversation = Conversation(audio_queue_in, audio_queue_out, function_manager)
    threads['conversation'] = threading.Thread(target=conversation.start, args=(shutdown_event,), daemon=True,
                                               name="Conversation")
    threads['conversation'].start()

def finish_call(threads, shutdown_event, audio_queue_in, audio_queue_out):
    shutdown_event.set()
    threads['rtp_receiver'].join()
    threads['rtp_sender'].join()
    threads['conversation'].join()

    clear_queue(audio_queue_in)
    clear_queue(audio_queue_out)

def register_functions(function_manager, path):
    full_path = os.path.abspath(path) if not os.path.isabs(path) else path
    sys.path.append(full_path)

    py_files = [file for file in os.listdir(full_path) if file.endswith('.py')]
    for file_name in py_files:
        module_name = file_name[:-3]
        module = importlib.import_module(module_name, package=None)
        if hasattr(module, 'GPT_FUNCTIONS'):
            for function_definition in module.GPT_FUNCTIONS:
                function_definition['name'] = module_name + '__' + function_definition['name']
                function_manager.register(function_definition)

def start():
    audio_queue_in = queue.Queue()
    audio_queue_out = queue.Queue()
    call_ended_event = threading.Event()
    function_manager = FunctionManager()

    register_functions(function_manager, './gpt_functions')

    threads = {
        'rtp_receiver': None,
        'rtp_sender': None,
        'sip_server': None,
        'conversation': None,
    }

    sip_server = SIPServer('0.0.0.0', 5060)

    sip_server.register_incoming_call_callback(partial(reset_event, call_ended_event))

    sip_server.register_incoming_call_callback(partial(start_rpt, threads, call_ended_event, audio_queue_in,
                                                       audio_queue_out))
    sip_server.register_incoming_call_callback(partial(start_conversation, threads,
                                                       call_ended_event, audio_queue_in, audio_queue_out,
                                                       function_manager))

    sip_server.register_call_ended_callback(partial(finish_call, threads, call_ended_event,
                                                    audio_queue_in, audio_queue_out))

    sip_thread_shutdown_event = threading.Event()
    threads['sip_server'] = threading.Thread(target=sip_server.start, args=(sip_thread_shutdown_event,), daemon=True,
                                             name="SIP server")
    threads['sip_server'].start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    sip_thread_shutdown_event.set()
    threads['sip_server'].join()

if __name__ == "__main__":
    start()
