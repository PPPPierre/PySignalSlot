from ..src.signal_slot import SignalInstance, Slot

def my_fun():
    print('fun')

print(type(my_fun))

# Nude signal - nude slot
s = SignalInstance()
@Slot()
def test():
    print('test!')
print(type(test))
s.connect(test)
s.emit()

# One input signal - one input slot
s = SignalInstance(float, arguments=['arg1'])
@Slot(float)
def test():
    print('test!')
print(s._call_types)
print(type(test))
s.connect(test)
s.emit()

class ReceiverThread(WorkerThread):

    def __init__(self):
        super().__init__()

    @Slot()
    def test(self):
        print("ReceiverThread Test!")


class SenderThread(WorkerThread):

    send_signal = Signal()

    def __init__(self):
        super().__init__()

print('Thread: {}, main thread'.format(threading.get_native_id()))

receiver_thread = ReceiverThread()
send_thread = SenderThread()

send_thread.send_signal.connect(receiver_thread.test)

nude_signal = SignalInstance()
nude_signal.connect(receiver_thread.test)

receiver_thread.start()
print('Thread: {}, {} started'.format(receiver_thread.native_id, receiver_thread))

send_thread.start()
print('Thread: {}, {} started'.format(send_thread.native_id, send_thread))

# Nude signal - class slot
nude_signal.emit()

# class signal - class slot
send_thread.send_signal.emit()

time.sleep(1)
receiver_thread.quit()
receiver_thread.join()
send_thread.quit()
send_thread.join()

class ReceiverClass():
    def __init__(self):
        pass
    @Slot()
    def test(self):
        print("Receiver Test!")

receiver = ReceiverClass()
send_thread = SenderThread()
send_thread.send_signal.connect(receiver.test)
send_thread.start()
send_thread.send_signal.emit()

time.sleep(1)
send_thread.quit()
send_thread.join()