import threading


def defer(func, *args, delay_seconds: float, **kwargs):
    timer = threading.Timer(delay_seconds, func, args=args, kwargs=kwargs)
    timer.daemon = True
    timer.start()
    return timer
