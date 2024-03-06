import weakref
import time

from functools import wraps
from traceback import format_exc
from logging import Logger, getLogger
from threading import Thread, Event, Condition, Lock, Timer, current_thread
from queue import Queue, Empty
from typing import Optional, Callable, List, Tuple, Dict, Set


class SignalInstance():

    def __init__(self, *input_pattern: List[Tuple[type, Optional[str]]]):
        '''
        The pattern format should be like:
        [(type1, argname1), (type2, argname2), ...]
        '''

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
                    raise SyntaxError('unamed argument follows named argument')
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
                f'invalid connect target {cbl}, it must be a callable instance or a SignalInstance'
            )
        w_cbl = weakref.ref(cbl.__func__) if hasattr(cbl, '__func__') else weakref.ref(cbl)
        w_owner = weakref.ref(cbl.__self__) if hasattr(cbl, '__self__') else None
        self._subscribers.add(
            (w_owner, w_cbl)
        )

    def __call__(self, *args, **kwargs):
        self.emit(*args, **kwargs)

    def emit(self, *args, **kwargs):
        # argument type check
        signal_args, signal_kwargs = self.transform_args(self._input_pattern, *args, **kwargs)

        # Activate each target
        for subscriber in self._subscribers.copy():
            w_owner, w_cbl = subscriber
            cbl = w_cbl()
            owner = w_owner() if w_owner else None

            if w_owner is not None and owner is None:
                self._subscribers.remove(subscriber)
                continue
            
            if hasattr(cbl, '_slot_patterns'):
                call_args, call_kwargs = None, None
                for slot_pattern in cbl._slot_patterns:
                    try:
                        call_args, call_kwargs = self.transform_args(slot_pattern, *signal_args, **signal_kwargs)
                    except TypeError:
                        continue
                if call_args is None:
                    raise TypeError(f'No available slot pattern can be triggered for slot {cbl}, get signal args: {signal_args}, signal kwargs: {signal_kwargs}, with slot patterns: {cbl._slot_patterns}, args: {args}, kwargs: {kwargs}, input_pattern: {self._input_pattern}, signal: {self}')
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

        ''' Args amount check '''
        if (len(args) + len(kwargs)) < len(input_pattern):
            raise TypeError(
                'the total amount of arguments is smaller than defined'
            )

        new_args = []
        new_kwargs = dict()
        j = 0

        for i, (call_type, name) in enumerate(input_pattern):
            
            ''' Argument attribute '''
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
            
            ''' Type check '''
            if not isinstance(arg, call_type):
                raise TypeError(
                    f'the type of the arg in index {i} should be {call_type}, get {arg} of type: {type(arg)}'
                )
            
            ''' Form new input args '''
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
        raise AttributeError('the signal can not be manually set')

    def __delete__(self, instance):
        raise AttributeError('the signal can not be manually deleted')


class Slot:

    def __init__(self, *args_pattern: List[Tuple[type, Optional[str]]]):
        '''
        The pattern format should be like:
        [(type1, argname1), (type2, argname2), ...]
        '''
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
                    raise SyntaxError('unamed argument follows named argument')
            else:
                if name in called_name:
                    raise SyntaxError("duplicate argument '{name}' in signal definition")
                called_name.add(name)
            pre_name = name

    def __call__(self, func):
        if not hasattr(func, '_slot_patterns'):
            func._slot_patterns = []
        func._slot_patterns.append(self._input_pattern)
        return func

class EventLoopThread(Thread):

    def __init__(self, parent=None):
        super().__init__()
        self._logger: Logger = getLogger('__main__')
        self._parent: Thread = parent
        if self._parent and isinstance(self._parent, EventLoopThread):
            self._parent._subthreads.append(self)
        self._subthreads: List[EventLoopThread] = []
        self._slot_queue: Queue = Queue()
        self._signal_avalaible: Condition = Condition(Lock())
        self._pause_event: Event = Event()
        self._exit_flag: bool = False

        self._loop_wait_flag: Dict[str, bool] = {}
        self._loop_timer: Dict[str, RepeatingTimer] = {}

        self.started: bool = False
        self.daemon: bool = True

    def _put_slot(self, slot: Callable, args, kwargs) -> None:
        with self._signal_avalaible:
            self._slot_queue.put((slot, args, kwargs))
            self._signal_avalaible.notify()

    def _add_loop(self, func: Callable, interval: float):
        if not hasattr(func, '__func__') or not hasattr(func, '__self__') or func.__self__ != self:
            self._logger.warning('Only instance methods can be added into the loop')
            return
        
        @wraps(func)
        def loop_func(self, *args, **kwargs):
            res = None
            try:
                res = func.__func__(self, *args, **kwargs)
            finally:
                self._loop_wait_flag[loop_func.__name__] = False
                return res
        
        def call_back():
            if not self._loop_wait_flag[loop_func.__name__]:
                self._loop_wait_flag[loop_func.__name__] = True
                self._put_slot(loop_func, [], {})
            
        timer = RepeatingTimer(interval=interval, function=call_back)
        self._loop_wait_flag.update({loop_func.__name__: False})
        self._loop_timer.update({loop_func.__name__: timer})
        timer.start()

    def run(self):
        ''' Before the event loop '''
        try:
            self.pre_work()
        except Exception:
            error_message = format_exc()
            self._logger.error(error_message)

        ''' During the event loop '''
        while True:
            if self._exit_flag:
                self._slot_queue.queue.clear()
                self.started = False
                break
            try:
                (slot, args, kwargs) = self._slot_queue.get(block=False)
                slot(self, *args, **kwargs)
            except Empty:
                with self._signal_avalaible:
                    if self._slot_queue.empty():
                        self._signal_avalaible.wait()
            except Exception:
                error_message = format_exc()
                self._logger.error(error_message)

        ''' After the event loop '''
        try:
            self.post_work()
        except Exception:
            error_message = format_exc()
            self._logger.error(error_message)
        for timer in self._loop_timer.values():
            if timer.is_alive():
                timer.cancel()
                timer.join()
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
        self._put_slot(self._set_exit_true.__func__, [], {})
        with self._signal_avalaible:
            self._signal_avalaible.notify()

    def _set_exit_true(self):
        self._exit_flag = True


class RepeatingTimer(Timer): 
    def run(self):
        while not self.finished.is_set():
            self.function(*self.args, **self.kwargs)
            self.finished.wait(self.interval)

