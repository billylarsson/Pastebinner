import threading, time
from queue import Queue
from PyQt6 import QtCore


def thread_spinner(signal, queue, lock):
    while True:
        runner_signal, wait = queue.get()
        lock.acquire()
        signal.main_thread.emit((runner_signal, lock, True,))
        lock.acquire()
        time.sleep(wait) if wait else ...
        signal.main_thread.emit((runner_signal, lock, False,))
        lock.acquire()
        queue.task_done()
        lock.release()


def main_thread_runner(args):
    signal, lock, start1 = args
    signal.start1.emit() if start1 else signal.start2.emit()
    lock.release()


class PoolSignal(QtCore.QObject):
    main_thread = QtCore.pyqtSignal(tuple)


class RunnerSignal(QtCore.QObject):
    start1 = QtCore.pyqtSignal()
    start2 = QtCore.pyqtSignal()


class CustomThreadPool:
    def __init__(self):
        self.dummy = lambda *args, **kwargs: None
        self.queue = Queue()
        self.lock = threading.Lock()
        self.signal = PoolSignal()
        self.signal.main_thread.connect(main_thread_runner)
        self.pipes = []
        threading.Thread(target=thread_spinner, args=(self.signal, self.queue, self.lock,), daemon=True).start()

    def __call__(self, executable1_fn=None, executable2_fn=None, wait: float = 0.0):
        signal = RunnerSignal()
        signal.start1.connect(executable1_fn or self.dummy)
        signal.start2.connect(executable2_fn or self.dummy)
        self.queue.put((signal, wait,))


def second_spinner(signal, queue, lock):
    while True:
        thread_fn, runner_signal, wait = queue.get()
        thread_fn()
        time.sleep(wait) if wait else ...
        lock.acquire()
        signal.slave_done.emit((runner_signal, lock,))
        lock.acquire()
        queue.task_done()
        lock.release()


def main_alerter(args):
    signal, lock = args
    signal.main_alert.emit()
    lock.release()


class ThreadThenMainPoolSignal(QtCore.QObject):
    slave_done = QtCore.pyqtSignal(tuple)


class ThreadThenMainRunnerSignal(QtCore.QObject):
    main_alert = QtCore.pyqtSignal()


class ThreadThenMain:
    def __init__(self):
        self.dummy = lambda *args, **kwargs: None
        self.queue = Queue()
        self.lock = threading.Lock()
        self.signal = ThreadThenMainPoolSignal()
        self.signal.slave_done.connect(main_alerter)
        self.pipes = []
        threading.Thread(target=second_spinner, args=(self.signal, self.queue, self.lock,), daemon=True).start()

    def __call__(self, thread_fn=None, main_fn=None, wait: float = 0.0):
        signal = ThreadThenMainRunnerSignal()
        signal.main_alert.connect(main_fn or self.dummy)
        self.queue.put((thread_fn or self.dummy, signal, wait,))
