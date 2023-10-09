import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from src.signal_slot import Signal, Slot
from unittest.mock import Mock, patch

def test_without_args():
    class MyClass:
        res = 0
        @Slot()
        def slot_func(self):
            self.res = 1

    test_ins = MyClass()
    signal = Signal()
    signal.connect(test_ins.slot_func)
    signal.emit()
    assert test_ins.res == 1

def test_args_1():
    class MyClass:
        res = 0
        @Slot((int, ))
        def slot_func(self, arg1):
            self.res = arg1

    test_ins = MyClass()
    signal = Signal((int, ))
    signal.connect(test_ins.slot_func)
    signal.emit(1)
    assert test_ins.res == 1