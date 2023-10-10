import threading
import types
import weakref
import time
import logging
import traceback
from threading import Thread, Event, Condition, Lock, Timer
from queue import Queue, Empty
from typing import overload, Optional, Any, Callable, List, Tuple
from functools import wraps


class SignalInstance():

    def __init__(self, *input_pattern: List[Tuple[type, Optional[str]]]):
        self._input_pattern = []
        self._subscribers = set()
        # check
        pre_name = None
        called_name = set()

        for couple in input_pattern:
            if len(couple) == 1:
                name = None
                self._input_pattern.append((couple[0], name))
            else:
                name = couple[1]
                self._input_pattern.append(couple)

            if name is None:
                if pre_name is not None:
                    raise SyntaxError("unamed argument follows named argument")
            else:
                if name in called_name:
                    raise SyntaxError("duplicate argument '{name}' in signal definition")
                called_name.add(name)
            pre_name = name
        
    def connect(self, cbl):
        if isinstance(cbl, SignalInstance):
            cbl = cbl.emit
        elif not callable(cbl):
            raise ValueError(
                f"invalid slot method {cbl}, must be a callable instance"
            )
        w_cbl = weakref.ref(cbl.__func__) if hasattr(cbl, "__func__") else weakref.ref(cbl)
        w_owner = weakref.ref(cbl.__self__) if hasattr(cbl, "__self__") else None
        self._subscribers.add(
            (w_owner, w_cbl)
        )

    def emit(self, *args, **kwargs):
        f"""
        {self._input_pattern}
        """

        # argument type check
        signal_args, signal_kwargs = self.transform_args(args, kwargs, self._input_pattern)
        for w_owner, w_cbl in self._subscribers:
            cbl = w_cbl()
            owner = w_owner() if w_owner else None
            if hasattr(cbl, '_slot_patterns'):
                slot_args, slot_kwargs = None, None
                for slot_pattern in cbl._slot_patterns:
                    try:
                        slot_args, slot_kwargs = self.transform_args(signal_args, signal_kwargs, slot_pattern)
                    except TypeError:
                        continue
                if slot_args is None:
                    raise TypeError("No available slot pattern can be triggered")
            else:
                slot_args = signal_args
                slot_kwargs = signal_kwargs

            if owner is None:
                cbl(*slot_args, **slot_kwargs)
                return
            if isinstance(owner, EventLoopThread) and hasattr(cbl, '_slot_patterns'):
                owner._put_slot(cbl, slot_args, slot_kwargs)
                return
            cbl(owner, *slot_args, **slot_kwargs)

    @staticmethod
    def transform_args(args, kwargs, input_pattern):
        if (len(args) + len(kwargs)) < len(input_pattern):
            raise TypeError(
                "the total amount of arguments is smaller than defined"
            )

        new_args = []
        new_kwargs = dict()
        j = 0

        for i, (call_type, name) in enumerate(input_pattern):
            
            if name is not None:
                if name in kwargs:
                    arg = kwargs.pop(name)
                else:
                    if j < len(args):
                        arg = args[j]
                        j += 1
                    else:
                        raise TypeError(
                            f"missing 1 required positional argument: '{name}'"
                        )
            else:
                if j < len(args):
                    arg = args[j]
                    j += 1
                else:
                    k, arg = list(kwargs.items())[j - len(args)]
                    kwargs.pop(k)
            
            if not isinstance(arg, call_type):
                raise TypeError(
                    f"the type of the arg in index {i} should be {call_type}"
                )
            
            if name is not None:
                if name in new_kwargs:
                    raise TypeError(
                        f"got multiple values for argument '{name}'"
                    )
                else:
                    new_kwargs[name] = arg
            else:
                new_args.append(arg)

        return new_args, new_kwargs


class Signal(SignalInstance):

    def __init__(self, *input_pattern: List[Tuple[type, Optional[str]]]):
        super().__init__(*input_pattern)
        self._signal_instances = {}
    
    def __get__(self, owner, ownertype=None) -> SignalInstance:
        if owner is None:
            return self
        if owner not in self._signal_instances:
            self._signal_instances[owner] = SignalInstance(*self._input_pattern)
        return self._signal_instances[owner]

    def __set__(self, instance, value):
        raise AttributeError("the signal can not be manually set")

    def __delete__(self, instance):
        raise AttributeError("the signal can not be manually deleted")


class Slot:

    def __init__(self, *args_pattern: List[Tuple[type, Optional[str]]]):
        self._input_pattern = []
        """
        The pattern format should be like =
        [(type1, argname1), (type2, argname2), ...]
        """
        pre_name = None
        called_name = set()
        for couple in args_pattern:
            if len(couple) == 1:
                name = None
                self._input_pattern.append((couple[0], name))
            else:
                name = couple[1]
                self._input_pattern.append(couple)
            if name is None:
                if pre_name is not None:
                    raise SyntaxError("unamed argument follows named argument")
            else:
                if name in called_name:
                    raise SyntaxError(" duplicate argument '{name}' in signal definition")
                called_name.add(name)
            pre_name = name

    def __call__(self, func):
        if not hasattr(func, "_slot_patterns"):
            func._slot_patterns = []
        func._slot_patterns.append(self._input_pattern)
        return func


class EventLoopThread(Thread):

    def __init__(self, parent=None):
        super().__init__()
        self._logger = logging.getLogger('__main__')
        self._parent = parent
        if self._parent:
            if isinstance(self._parent, EventLoopThread):
                self._parent._subthreads.append(self)
        self._subthreads = []
        self._subthreads: List[EventLoopThread]
        self._slot_queue = Queue()
        self._signal_avalaibel = Condition(Lock())
        self._pause_event = Event()
        self._exit_flag = False
        self._main_work_stop = True
        self.daemon = True

    def _put_slot(self, slot, args, kwargs):
        with self._signal_avalaibel:
            # self._logger.debug("Instance: {}, put slot: {}".format(self, slot))
            self._slot_queue.put((slot, args, kwargs))
            self._signal_avalaibel.notify()
            # print("Thread: {}, finish put: {}".format(threading.get_native_id(), slot))

    def run(self):
        # Before slot method loop
        try:
            self.init_work()
        except Exception:
            error_message = traceback.format_exc()
            self._logger.error(error_message)
        self._put_slot(self._main_work_slot.__func__, [], {})

        # Slot method loop
        while True:
            if self._exit_flag:
                self._slot_queue.queue.clear()
                break
            try:
                (slot, args, kwargs) = self._slot_queue.get(block=False)
                slot(self, *args, **kwargs)
            except Empty:
                with self._signal_avalaibel:
                    if self._slot_queue.empty():
                        self._signal_avalaibel.wait()
            except Exception:
                error_message = traceback.format_exc()
                self._logger.error(error_message)

        # After slot method loop
        try:
            self.finalize_work()
        except Exception:
            error_message = traceback.format_exc()
            self._logger.error(error_message)
        for sub_thread in self._subthreads:
            if sub_thread.is_alive():
                sub_thread.quit()
                sub_thread.join()

    def main_work_loop(self):
        self._main_work_stop = False

    def _main_work_slot(self):
        self.main_work_loop()
        if self._main_work_stop:
            self._put_slot(self._main_work_slot.__func__, [], {})

    def stop_main_work_loop(self):
        self._main_work_stop = False

    def init_work(self):
        pass

    def finalize_work(self):
        pass

    def start(self) -> None:
        self._exit_flag = False
        return super().start()

    def pause(self):
        self._pause_event.clear()
        self._pause_event.wait()

    def resume(self):
        self._pause_event.set()

    def quit(self):
        self._logger.info('Quit {}'.format(self))
        self._put_slot(self._set_exit_true.__func__, [], {})
        with self._signal_avalaibel:
            self._signal_avalaibel.notify()

    def _set_exit_true(self):
        self._exit_flag = True


class RepeatingTimer(Timer): 
    def run(self):
        while not self.finished.is_set():
            self.function(*self.args, **self.kwargs)
            self.finished.wait(self.interval)

