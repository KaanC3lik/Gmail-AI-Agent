import threading

_lock = threading.Lock()
last_history_id = None

def get_last_history_id():
    with _lock:
        return last_history_id

def set_last_history_id(new_id):
    global last_history_id
    with _lock:
        last_history_id = new_id
