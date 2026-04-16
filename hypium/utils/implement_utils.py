class NotImplementObj:

    def __init__(self, msg=""):
        self._msg = msg
    def __getattr__(self, item):
        raise NotImplementedError(self._msg)

def generic_deco(func):
    return func

class _GenericObject:
    def __call__(self, *args, **kwargs):
        return None

    def __getattr__(self, item):
        return _GenericObject()


GenericObject = _GenericObject()
