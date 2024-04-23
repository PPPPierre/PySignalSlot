import weakref
import asyncio

from typing import Optional, Callable, List, Tuple, Awaitable

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

            if asyncio.iscoroutinefunction(cbl):
                if owner is None:
                    task = cbl(*call_args, **call_kwargs)
                else:
                    task = cbl(owner, *call_args, **call_kwargs)
                
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:  # 'RuntimeError: There is no current event loop...'
                    loop = None
                if loop and loop.is_running():
                    loop.create_task(task)
                else:
                    asyncio.create_task(task)
            else:
                if owner is None:
                    cbl(*call_args, **call_kwargs)
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
        
class AsyncTimer:
    def __init__(self, timeout: float, callback: Awaitable, once: bool=False):
        self._timeout: float = timeout
        self._callback: Awaitable = callback
        self._once: bool = once
        self._started: bool = False
        self._task: Optional[asyncio.Task] = None

    @property
    def is_alive(self):
        if self._task is None:
            return False
        if self._task.cancelled():
            return False
        if self._task.done():
            return False
        return True

    def start(self):
        if self._started:
            return
        if self._once:
            self._task = asyncio.create_task(self._job_once())
        else:
            self._task = asyncio.create_task(self._job_loop())

    async def _job_once(self):
        await asyncio.sleep(self._timeout)
        await self._callback()

    async def _job_loop(self):
        while True:
            await asyncio.sleep(self._timeout)
            await self._callback()
            
    def cancel(self):
        if not self._started:
            return
        self._task.cancel()
