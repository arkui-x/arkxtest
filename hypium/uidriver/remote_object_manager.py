import weakref
from typing import Set
from weakref import WeakSet, proxy
from .logger import hypium_inner_log
from hypium.uidriver import setup_device


class RemoteObjectManager:

    def __init__(self, device) -> None:
        self.total_register_object = 0
        self.total_removed_object = 0
        self.total_clear_backend_object = 0
        self.batch_size = 20
        # save object has been released
        self.garbages = set()
        self.active_objects = WeakSet()
        self.device = weakref.proxy(device)

    def objects_disconnected(self):
        hypium_inner_log.debug("total active number: " + str(len(self.active_objects)))
        for item in self.active_objects:
            item.deactivate()
    
    def remove_object(self, back_obj_ref: str):
        self.total_removed_object += 1
        self.garbages.add(back_obj_ref)
    
    def need_clean_remote_objects(self):
        if len(self.garbages) > self.batch_size:
            return True
        else:
            return False

    def on_remote_state_change(self, **kwargs):
        self.total_removed_object += len(self.garbages)
        self.clear_garbage()
        self.objects_disconnected()
        device = self.device
        # reset device when disconnected
        if device is not None:
            setup_device.reset_device(self.device)

    def set_remote_state_change_listener(self, device):
        if getattr(device, "proxy_listener", None) != self.on_remote_state_change:
            setattr(device, "proxy_listener", self.on_remote_state_change)

    def clear_garbage(self):
        hypium_inner_log.debug("clear remote objects, current: %d, remain %d, total delete: %d, total delete backend: %d, total create: %d" %
                               (len(self.garbages), len(self.active_objects), self.total_removed_object, self.total_clear_backend_object, self.total_register_object))
        self.garbages.clear()
    
    def get_garbages(self) -> set:
        return self.garbages

    def add_object(self, obj):
        remains_count = len(self.active_objects)
        self.active_objects.add(obj)
        remains_count_after = len(self.active_objects)
        if remains_count_after > remains_count:
            self.total_register_object += 1

    def release_all(self):
        """release all remote objects"""
        self.batch_size = 0
        for item in self.active_objects:
            item.release()

