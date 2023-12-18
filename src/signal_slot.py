import weakref
import logging
import traceback
from threading import Thread, Event, Condition, Lock, Timer
from queue import Queue, Empty
from typing import Optional, Callable, List, Tuple


class SignalInstance():

    def __init__(self, *input_pattern: List[Tuple[type, Optional[str]]]):
        """
        The pattern format should be like:
        [(type1, argname1), (type2, argname2), ...]
        """

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
        
    def connect(self, cbl: Callable):
        if isinstance(cbl, SignalInstance):
            cbl = cbl.emit
        elif not callable(cbl):
            raise ValueError(
                f"invalid connect target {cbl}, it must be a callable instance or a SignalInstance"
            )
        w_cbl = weakref.ref(cbl.__func__) if hasattr(cbl, "__func__") else weakref.ref(cbl)
        w_owner = weakref.ref(cbl.__self__) if hasattr(cbl, "__self__") else None
        self._subscribers.add(
            (w_owner, w_cbl)
        )

    def __call__(self, *args, **kwargs):
        self.emit(*args, **kwargs)

    def emit(self, *args, **kwargs):
        # argument type check
        signal_args, signal_kwargs = self.transform_args(self._input_pattern, *args, **kwargs)

        # Activate each target
        for w_owner, w_cbl in self._subscribers:
            cbl = w_cbl()
            owner = w_owner() if w_owner else None
            if w_owner is not None and owner is None:
                raise ReferenceError("The owner of the slot method has been garbage collected")
            if hasattr(cbl, '_slot_patterns'):
                call_args, call_kwargs = None, None
                for slot_pattern in cbl._slot_patterns:
                    try:
                        call_args, call_kwargs = self.transform_args(slot_pattern, *signal_args, **signal_kwargs)
                    except TypeError:
                        continue
                if call_args is None:
                    raise TypeError(f"No available slot pattern can be triggered for slot {cbl}, get signal args: {signal_args}, signal kwargs: {signal_kwargs}, with slot patterns: {cbl._slot_patterns}, args: {args}, kwargs: {kwargs}, input_pattern: {self._input_pattern}, signal: {self}")
            elif isinstance(owner, SignalInstance):
                call_args, call_kwargs = self.transform_args(owner._input_pattern, *signal_args, **signal_kwargs)
            else:
                call_args = signal_args
                call_kwargs = signal_kwargs

            if owner is None:
                cbl(*call_args, **call_kwargs)
            elif isinstance(owner, EventLoopThread) and hasattr(cbl, '_slot_patterns'):
                owner._put_slot(cbl, call_args, call_kwargs)
            else:
                cbl(owner, *call_args, **call_kwargs)

    @staticmethod
    def transform_args(input_pattern, *args, **kwargs):

        """ Args amount check """
        if (len(args) + len(kwargs)) < len(input_pattern):
            raise TypeError(
                "the total amount of arguments is smaller than defined"
            )

        new_args = []
        new_kwargs = dict()
        j = 0

        for i, (call_type, name) in enumerate(input_pattern):
            
            """ Argument attribute """
            if name is None:
                # For arguments without name
                if j < len(args):
                    arg = args[j]
                    j += 1
                else:
                    k, arg = list(kwargs.items())[j - len(args)]
                    kwargs.pop(k)
            else:
                # For arguments with a name
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
            
            """ Type check """
            if not isinstance(arg, call_type):
                raise TypeError(
                    f"the type of the arg in index {i} should be {call_type}, get {arg} of type: {type(arg)}"
                )
            
            """ Form new input args """
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
        """
        The pattern format should be like:
        [(type1, argname1), (type2, argname2), ...]
        """
        self._input_pattern = []
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
        if self._parent and isinstance(self._parent, EventLoopThread):
            self._parent._subthreads.append(self)
        self._subthreads = []
        self._subthreads: List[EventLoopThread]
        self._slot_queue = Queue()
        self._signal_avalaibel = Condition(Lock())
        self._pause_event = Event()
        self._exit_flag = False
        self._main_work_stop = True
        self.started = False
        self.daemon = True

    def _put_slot(self, slot, args, kwargs):
        with self._signal_avalaibel:
            self._slot_queue.put((slot, args, kwargs))
            self._signal_avalaibel.notify()

    def run(self):
        """ Before the event loop """
        try:
            self.pre_work()
        except Exception:
            error_message = traceback.format_exc()
            self._logger.error(error_message)
        self._put_slot(self._main_work_slot.__func__, [], {})

        """ During the event loop """
        while True:
            if self._exit_flag:
                self._slot_queue.queue.clear()
                self.started = False
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

        """ After the event loop """
        try:
            self.post_work()
        except Exception:
            error_message = traceback.format_exc()
            self._logger.error(error_message)
        for sub_thread in self._subthreads:
            if sub_thread.is_alive():
                sub_thread.quit()
                sub_thread.join()

    def pre_work(self):
        # Work before the event loop started
        pass

    def post_work(self):
        # Work after the event loop ended
        pass

    def main_work(self):
        self._main_work_stop = False

    def _main_work_slot(self):
        self.main_work()
        if self._main_work_stop:
            self._put_slot(self._main_work_slot.__func__, [], {})

    def stop_main_work(self):
        self._main_work_stop = False

    def start(self) -> None:
        if self.started:
            return
        else:
            self.started = True
            self._exit_flag = False
            return super().start()

    def pause(self):
        self._pause_event.clear()
        self._pause_event.wait()

    def resume(self):
        self._pause_event.set()

    def quit(self):
        # self._logger.info(f'Quit event loop thread')
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

