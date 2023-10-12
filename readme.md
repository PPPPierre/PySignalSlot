# PySignalSlot

A Python-based Signal-Slot Mechanism. Inspired by the Qt Signal-Slot mechanism, PySignalSlot offers a simple and lightweight way to implement decoupled communication between Python objects. Whether you are building GUI applications, games, or complex systems, this library helps ensure that your components remain modular and easy to maintain.

## Prerequisites

- Python: 3.10 or higher

## Advantages

Using the Signal - Slot system provides mainly two advantages:

- Type Security: This system enforces type checking, ensuring that signals and slots are compatible. This leads to safer code by preventing type-related issues at runtime.
- Loose Coupling: By design, the Signal - Slot mechanism promotes loose coupling between components. This results in more modular and maintainable code, as individual components can be developed, tested, and modified independently.

## Usage

The provided code demonstrates a Signal-Slot mechanism within a multithreaded context:

1. Define two classes, `Sender` and `Receiver`, both inheriting from `EventLoopThread`. The `Sender` class has a `signal`. The `Receiver` class possesses a `Slot` named `test` that captures its thread's native ID.
    ```python
    # Define EventLoopThread classes, signals and slots
    class Sender(EventLoopThread):
        signal = Signal()
        def __init__(self):
            super().__init__()

    class Receiver(EventLoopThread):

        def __init__(self):
            super().__init__()
            self.thread_id = None
        
        @Slot()
        def test(self):
            self.thread_id = threading.get_native_id()
    ```

2. Initiate and start an instance of the `Receiver`, initiating its event loop. Initiate an instance of the `Sender` and connect its `signal` to the `test` slot of the Receiver instance.
    ```python
    # Initialise instances and start loop
    receiver = Receiver()
    sender = Sender()
    receiver.start()
    # Connect the signal
    sender.signal.connect(receiver.test)
    ```

3. Emitting the `signal` in the main thread, then you can observed the `test` slot of the `Receiver` instance is executed in its event loop in a different thread.
    ```python
    # Signal emits
    sender.signal.emit()
    thread_id = threading.get_native_id()
    receiver.quit()
    sender.quit()
    assert receiver.thread_id != thread_id
    ```

