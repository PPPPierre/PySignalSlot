import sys
import os
import pytest
import threading

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from src.signal_slot import Signal, Slot, EventLoopThread

def test_without_args():
    class Receiver(EventLoopThread):

        def __init__(self):
            super().__init__()
            self.thread_id = None
        
        @Slot()
        def test(self):
            self.thread_id = threading.get_native_id()

    class Sender(EventLoopThread):
        signal = Signal()
        def __init__(self):
            super().__init__()

    receiver = Receiver()
    sender = Sender()
    receiver.start()
    sender.signal.connect(receiver.test)
    sender.signal.emit()
    thread_id = threading.get_native_id()
    receiver.quit()
    sender.quit()
    assert receiver.thread_id != thread_id
    