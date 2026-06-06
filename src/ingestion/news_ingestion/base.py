from abc import ABC, abstractmethod


class BaseNewsSource(ABC):

    @abstractmethod
    def fetch(self, query: str):
        pass
