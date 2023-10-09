import sys
import os
import pytest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from src.signal_slot import Signal, Slot
from unittest.mock import Mock, patch

def test_without_args():
    signal = Signal()
    @Slot()
    def test():
        nonlocal res
        res = 1
    res = 0
    signal.connect(test)
    signal.emit()
    assert res == 1

def test_args_1():
    signal = Signal((int, ))
    @Slot((int, ))
    def test(arg1: int):
        nonlocal res
        res = arg1
    res = None
    signal.connect(test)
    signal.emit(1)
    assert res == 1

def test_args_2():
    signal = Signal((int, ), (str, ))
    @Slot((int, ), (str, ))
    def test(arg1, arg2):
        nonlocal res1, res2
        res1, res2 = arg1, arg2
    res1, res2 = None, None
    signal.connect(test)
    signal.emit(1, '0')
    assert res1 == 1
    assert res2 == '0'

def test_kwargs_1():
    signal = Signal((int, 'arg1'))
    @Slot((int, 'arg1'))
    def test(arg1: int):
        nonlocal res
        res = arg1
    res = None
    signal.connect(test)
    signal.emit(1)
    assert res == 1

def test_kwargs_2():
    signal = Signal((int, 'arg1'), (str, 'arg2'))
    @Slot((int, 'arg1'), (str, 'arg2'))
    def test(arg1, arg2):
        nonlocal res1, res2
        res1, res2 = arg1, arg2
    res1, res2 = None, None
    signal.connect(test)
    signal.emit(1, '0')
    assert res1 == 1
    assert res2 == '0'

def test_args_kwargs_1():
    signal = Signal((int, ), (str, 'arg2'))
    @Slot((int, ), (str, 'arg2'))
    def test(arg1, arg2):
        nonlocal res1, res2
        res1, res2 = arg1, arg2
    res1, res2 = None, None
    signal.connect(test)
    signal.emit(1, '0')
    assert res1 == 1
    assert res2 == '0'

def test_args_kwargs_2():
    signal = Signal((int, ), (str, 'arg2'))
    @Slot((int, 'arg1'), (str, 'arg2'))
    def test(arg1, arg2):
        nonlocal res1, res2
        res1, res2 = arg1, arg2
    res1, res2 = None, None
    signal.connect(test)
    signal.emit(1, '0')
    assert res1 == 1
    assert res2 == '0'

def test_args_kwargs_3():
    signal = Signal((int, ), (str, ))
    @Slot((int, 'arg1'), (str, 'arg2'))
    def test(arg1, arg2):
        nonlocal res1, res2
        res1, res2 = arg1, arg2
    res1, res2 = None, None
    signal.connect(test)
    signal.emit(1, '0')
    assert res1 == 1
    assert res2 == '0'

def test_args_kwargs_4():
    signal = Signal((int, 'arg1'), (str, 'arg2'))
    @Slot((int, ), (str, ))
    def test(arg1, arg2):
        nonlocal res1, res2
        res1, res2 = arg1, arg2
    res1, res2 = None, None
    signal.connect(test)
    signal.emit(1, '0')
    assert res1 == 1
    assert res2 == '0'

def test_args_kwargs_5():
    signal = Signal((int, 'arg1'), (str, 'arg2'))
    @Slot((int, ), (int, 'arg1'))
    def test(arg, arg1):
        nonlocal res1, res2
        res1, res2 = arg, arg1
    res1, res2 = None, None
    signal.connect(test)
    with pytest.raises(TypeError):
        signal.emit(1, '0')
        
def test_multi_signal_one_slot_1():
    res = None
    signal_int = Signal((int, ))
    signal_str = Signal((str, ))
    @Slot((int, ))
    @Slot((str, ))
    def test(arg1):
        nonlocal res
        res = arg1
    signal_int.connect(test)
    signal_str.connect(test)
    signal_int.emit(1)
    assert res == 1
    signal_str.emit('0')
    assert res == '0'

def test_multi_signal_one_slot_2():
    res = None
    signal_int = Signal((int, ))
    signal_str = Signal((str, ))
    signal_int_str = Signal((int, ), (str, ))
    @Slot((int, ))
    @Slot((str, ))
    def test(arg1):
        nonlocal res
        res = arg1
    signal_int.connect(test)
    signal_str.connect(test)
    signal_int_str.connect(test)
    signal_int.emit(1)
    assert res == 1
    signal_str.emit('0')
    assert res == '0'
    signal_int_str.emit(2, '1')
    assert res == 2

def test_loose_coupling_1():
    signal = Signal((int, ), (str, ))
    @Slot()
    def test():
        nonlocal res
        res = 1
    res = 0
    signal.connect(test)
    signal.emit(0, '0')
    assert res == 1

def test_loose_coupling_2():
    signal = Signal((int, ), (str, ))
    @Slot()
    def test(arg1=1):
        nonlocal res
        res = arg1
    res = 0
    signal.connect(test)
    signal.emit(0, '0')
    assert res == 1

def test_loose_coupling_3():
    res = None
    signal = Signal((int, ), (str, ))
    @Slot((int, ))
    def test(arg1):
        nonlocal res
        res = arg1
    signal.connect(test)
    signal.emit(1, '0')
    assert res == 1

def test_loose_coupling_4():
    signal = Signal((int, ), (str, ))
    @Slot((int, ))
    def test(arg1, arg2='1'):
        nonlocal res1, res2
        res1, res2 = arg1, arg2
    res1, res2 = None, None
    signal.connect(test)
    signal.emit(1, '0')
    assert res1 == 1
    assert res2 == '1'

def test_loose_coupling_5():
    res = None
    signal = Signal((int, ), (str, 'arg2'))
    @Slot((str, 'arg2'))
    def test(arg2):
        nonlocal res
        res = arg2
    signal.connect(test)
    signal.emit(1, '0')
    assert res == '0'

def test_loose_coupling_6():
    res = None
    signal = Signal((int, 'arg1'), (str, 'arg2'))
    @Slot((str, 'arg2'))
    def test(arg2):
        nonlocal res
        res = arg2
    signal.connect(test)
    signal.emit(1, '0')
    assert res == '0'

