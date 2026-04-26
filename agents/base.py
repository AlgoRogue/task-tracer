from abc import ABC, abstractmethod
import tasks


class TemelAjan(ABC):
    @property
    @abstractmethod
    def ajan_adi(self) -> str: ...

    @abstractmethod
    def calistir(self) -> dict: ...

    def olay_kaydet(self, olay_turu: str, mesaj: str, meta=None) -> None:
        tasks.ajan_olayi_kaydet(self.ajan_adi, olay_turu, mesaj, meta)
