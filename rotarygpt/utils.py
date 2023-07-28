import queue

def clear_queue(queue_to_empty):
    while not queue_to_empty.empty():
        try:
            queue_to_empty.get(block=False)
        except queue.Empty:
            continue
        queue_to_empty.task_done()