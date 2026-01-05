
from threading import Thread, Event

class Timer(Thread):
    """
    Simple timer class that's better than the one provided by threading.Timer()
    """
    def __init__(self, interval: float, method, arg = None, periodic = False, manual = False):
        """
        Parameters
        ----------
        interval: float
            Timer interval in seconds
        method: Any
            Callback on timer expiration
        arg: Any
            Argument for method()
        periodic: bool
            If set, the timer will continue executing after expiration. May be paired with manual
        manual: bool
            If set, the timer must be manually reset after expiration
        """
        Thread.__init__(self)
        self._interval = interval
        self._cancel_event = Event()
        self._relaunch_event = Event()
        self._periodic = periodic
        self._arg = arg
        self._method = method
        self._manual = manual

    @property
    def interval(self) -> float:
        return self._interval

    @interval.setter
    def interval(self, i: float):
        """
        Sets the interval to a specific value.
        """
        self._interval = i

    @property
    def periodic(self) -> bool:
        return self._periodic
    
    @property
    def manual(self) -> bool:
        return self._manual

    def reset(self):
        """
        Reset the timer
        Manual timers need to call this explicitly to get a relaunch and initial launch.
        For periodic timers, this method is equivalent to cancel()
        """
        self._cancel_event.set()
        self._relaunch_event.set()

    def cancel(self):
        """
        Cancels the timer.
        Periodic timers will relaunch immediately.
        For manual timers, this will halt the timer until a subsequent call to reset() is performed.
        """
        self._cancel_event.set()

    def run(self):
        """Do not call me directly! Use start() instead!"""
        while True:
            # manual threads must be relaunched explicitly
            if self._manual:
                self._relaunch_event.wait()
            self._relaunch_event.clear()

            # Wait for a timeout, or cancellation
            self._cancel_event.clear()
            if self._cancel_event.wait(self._interval):
                self._cancel_event.clear() # Timer cancelled, restart
                if not self._periodic:
                    return
                continue
            self._cancel_event.clear()

            if self._arg:
                self._method(self._arg)
            else:
                self._method()

            if not self._periodic:
                return