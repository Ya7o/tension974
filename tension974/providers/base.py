from abc import ABC, abstractmethod
from ..models import FetchResult


class FetchProvider(ABC):
    @abstractmethod
    def fetch(self, url: str) -> FetchResult:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...
