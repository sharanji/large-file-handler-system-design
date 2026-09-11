import threading

DEFAULT_DELAY_SECONDS = 3


def tasks_defer(func, *args, delay_seconds=DEFAULT_DELAY_SECONDS, **kwargs):
    timer = threading.Timer(delay_seconds, func, args=args, kwargs=kwargs)
    timer.daemon = True
    timer.start()
    return timer
