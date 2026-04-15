import traceback
from devicetest.log.logger import platform_logger

hypium_event_manager_log = platform_logger("HypiumEventManager")


class EventManager:
    EVENT_UI_ACTION_START = 'ui_action_start'

    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event_type, subscriber_id, callback):
        if event_type not in self.subscribers.keys():
            self.subscribers[event_type] = {
                subscriber_id: callback
            }
        else:
            if subscriber_id in self.subscribers.keys():
                hypium_event_manager_log.warning(f"listener {subscriber_id} has been replaced by f{callback}")
            self.subscribers[event_type][subscriber_id] = callback

    def unsubscribe(self, event_type, subscriber_id):
        if event_type not in self.subscribers.keys():
            hypium_event_manager_log.warning(f"No such event type [{event_type}]")
            return
        else:
            event_subscribers = self.subscribers.get(event_type)
            if subscriber_id not in event_subscribers.keys():
                hypium_event_manager_log.warning(f"No such subscriber [{subscriber_id}] in [{event_type}]")
                return
            else:
                event_subscribers.pop(subscriber_id)

    def unsubscribe_all(self, event_type):
        if event_type not in self.subscribers.keys():
            hypium_event_manager_log.warning(f"No such event type [{event_type}]")
            return
        else:
            # 清空所有subscriber
            self.subscribers[event_type] = {}

    def notify_event(self, event_type, params: dict = None):
        event_subscribers = self.subscribers.get(event_type, {})
        for subscriber_id, callback in event_subscribers.items():
            hypium_event_manager_log.debug(f"Notify event {event_type} to {subscriber_id}")
            try:
                callback(event_type, params)
            except Exception as e:
                hypium_event_manager_log.error(f"Failed to notify event {event_type} to {subscriber_id}")
                hypium_event_manager_log.error(traceback.format_exc())
