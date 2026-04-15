import threading


class _ThreadLocalVar:

    def __init__(self):
        self._global_var = threading.local()

    def __getattr__(self, item):
        if not hasattr(self._global_var, item):
            return None
        return getattr(self._global_var, item)

    def __setattr__(self, key, value):
        if key == "_global_var":
            self.__dict__[key] = value
        else:
            setattr(self._global_var, key, value)


class _GlobalVar:

    def __init__(self):
        self._attrs = dict()

    def __setattr__(self, key, value):
        if key == "_attrs":
            self.__dict__[key] = value
        else:
            self._attrs[key] = value

    def __getattr__(self, item):
        return self.attrs.get(item, None)


ThreadLocalVar = _ThreadLocalVar()
GlobalVar = _GlobalVar()
