from abc import abstractmethod, ABC


class ILog(ABC):

    @abstractmethod
    def error(self, msg):
        pass

    @abstractmethod
    def debug(self, msg):
        pass

    @abstractmethod
    def info(self, msg):
        pass

    @abstractmethod
    def warning(self, msg):
        pass
