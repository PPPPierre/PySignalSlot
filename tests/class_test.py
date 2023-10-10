import sys
import os
import pytest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from src.signal_slot import Signal, Slot


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

def test_args_2():
    class MyClass:
        res1, res2 = None, None
        @Slot((int, ), (str, ))
        def slot_func(self, arg1, arg2):
            self.res1, self.res2 = arg1, arg2
    
    test_ins = MyClass()
    signal = Signal((int, ), (str, ))
    signal.connect(test_ins.slot_func)
    signal.emit(1, '0')
    assert test_ins.res1 == 1
    assert test_ins.res2 == '0'

def test_kwargs_1():
    class MyClass:
        res = None
        @Slot((int, 'arg1'))
        def slot_func(self, arg1: int):
            self.res = arg1
    
    test_ins = MyClass()
    signal = Signal((int, 'arg1'))
    signal.connect(test_ins.slot_func)
    signal.emit(1)
    assert test_ins.res == 1

def test_kwargs_2():
    class MyClass:
        res1, res2 = None, None
        @Slot((int, 'arg1'), (str, 'arg2'))
        def slot_func(self, arg1, arg2):
            self.res1, self.res2 = arg1, arg2
    
    test_ins = MyClass()
    signal = Signal((int, 'arg1'), (str, 'arg2'))
    signal.connect(test_ins.slot_func)
    signal.emit(1, '0')
    assert test_ins.res1 == 1
    assert test_ins.res2 == '0'

def test_args_kwargs_1():
    class MyClass:
        res1, res2 = None, None
        @Slot((int, ), (str, 'arg2'))
        def slot_func(self, arg1, arg2):
            self.res1, self.res2 = arg1, arg2

    test_ins = MyClass()
    signal = Signal((int, ), (str, 'arg2'))
    signal.connect(test_ins.slot_func)
    signal.emit(1, '0')
    assert test_ins.res1 == 1
    assert test_ins.res2 == '0'

def test_args_kwargs_2():
    class MyClass:
        res1, res2 = None, None
        @Slot((int, 'arg1'), (str, 'arg2'))
        def slot_func(self, arg1, arg2):
            self.res1, self.res2 = arg1, arg2
    
    test_ins = MyClass()
    signal = Signal((int, ), (str, 'arg2'))
    signal.connect(test_ins.slot_func)
    signal.emit(1, '0')
    assert test_ins.res1 == 1
    assert test_ins.res2 == '0'

def test_args_kwargs_3():
    class MyClass:
        res1, res2 = None, None
        @Slot((int, 'arg1'), (str, 'arg2'))
        def slot_func(self, arg1, arg2):
            self.res1, self.res2 = arg1, arg2

    test_ins = MyClass()
    signal = Signal((int, ), (str, ))
    signal.connect(test_ins.slot_func)
    signal.emit(1, '0')
    assert test_ins.res1 == 1
    assert test_ins.res2 == '0'

def test_args_kwargs_4():
    class MyClass:
        res1, res2 = None, None
        @Slot((int, ), (str, ))
        def slot_func(self, arg1, arg2):
            self.res1, self.res2 = arg1, arg2

    test_ins = MyClass()
    signal = Signal((int, 'arg1'), (str, 'arg2'))
    signal.connect(test_ins.slot_func)
    signal.emit(1, '0')
    assert test_ins.res1 == 1
    assert test_ins.res2 == '0'

def test_args_kwargs_5():
    class MyClass:
        res1, res2 = None, None
        @Slot((int, ), (int, 'arg1'))
        def slot_func(self, arg, arg1):
            self.res1, self.res2 = arg, arg1
    
    test_ins = MyClass()
    signal = Signal((int, 'arg1'), (str, 'arg2'))
    signal.connect(test_ins.slot_func)
    with pytest.raises(TypeError):
        signal.emit(1, '0')
        
def test_multi_signal_one_slot_1():
    class MyClass:
        res = None
        @Slot((int, ))
        @Slot((str, ))
        def slot_func(self, arg1):
            self.res = arg1

    test_ins = MyClass()
    signal_int = Signal((int, ))
    signal_str = Signal((str, ))
    signal_int.connect(test_ins.slot_func)
    signal_str.connect(test_ins.slot_func)
    signal_int.emit(1)
    assert test_ins.res == 1
    signal_str.emit('0')
    assert test_ins.res == '0'

def test_multi_signal_one_slot_2():
    class MyClass:
        res = None
        @Slot((int, ))
        @Slot((str, ))
        def slot_func(self, arg1):
            self.res = arg1
    
    test_ins = MyClass()
    signal_int = Signal((int, ))
    signal_str = Signal((str, ))
    signal_int_str = Signal((int, ), (str, ))
    signal_int.connect(test_ins.slot_func)
    signal_str.connect(test_ins.slot_func)
    signal_int_str.connect(test_ins.slot_func)
    signal_int.emit(1)
    assert test_ins.res == 1
    signal_str.emit('0')
    assert test_ins.res == '0'
    signal_int_str.emit(2, '1')
    assert test_ins.res == 2

def test_loose_coupling_1():
    class MyClass:
        res = 0
        @Slot()
        def slot_func(self):
            self.res = 1
    
    test_ins = MyClass()
    signal = Signal((int, ), (str, ))
    signal.connect(test_ins.slot_func)
    signal.emit(0, '0')
    assert test_ins.res == 1

def test_loose_coupling_2():
    class MyClass:
        res = 0
        @Slot()
        def slot_func(self, arg1=1):
            self.res = arg1

    test_ins = MyClass()
    signal = Signal((int, ), (str, ))
    signal.connect(test_ins.slot_func)
    signal.emit(0, '0')
    assert test_ins.res == 1

def test_loose_coupling_3():
    class MyClass:
        res = None
        @Slot((int, ))
        def slot_func(self, arg1):
            self.res = arg1
    
    test_ins = MyClass()
    signal = Signal((int, ), (str, ))
    signal.connect(test_ins.slot_func)
    signal.emit(1, '0')
    assert test_ins.res == 1

def test_loose_coupling_4():
    class MyClass:
        res1, res2 = None, None
        @Slot((int, ))
        def slot_func(self, arg1, arg2='1'):
            self.res1, self.res2 = arg1, arg2
    
    test_ins = MyClass()
    signal = Signal((int, ), (str, ))
    signal.connect(test_ins.slot_func)
    signal.emit(1, '0')
    assert test_ins.res1 == 1
    assert test_ins.res2 == '1'

def test_loose_coupling_5():
    class MyClass:
        res = None
        @Slot((str, 'arg2'))
        def slot_func(self, arg2):
            self.res = arg2

    test_ins = MyClass()
    signal = Signal((int, ), (str, 'arg2'))
    signal.connect(test_ins.slot_func)
    signal.emit(1, '0')
    assert test_ins.res == '0'

def test_loose_coupling_6():
    class MyClass:
        res = None
        @Slot((str, 'arg2'))
        def slot_func(self, arg2):
            self.res = arg2
    
    test_ins = MyClass()
    signal = Signal((int, 'arg1'), (str, 'arg2'))
    signal.connect(test_ins.slot_func)
    signal.emit(1, '0')
    assert test_ins.res == '0'