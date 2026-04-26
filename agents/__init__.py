from agents.giris import GirisAjan
from agents.skor import SkorAjan
from agents.hatirlatma import HatirlatmaAjan
from agents.takvim import TakvimAjan
from agents.oncelik import OncelikAjan

_AJAN_KAYDEDICISI = {
    "GirisAjan": GirisAjan,
    "SkorAjan": SkorAjan,
    "HatirlatmaAjan": HatirlatmaAjan,
    "TakvimAjan": TakvimAjan,
    "OncelikAjan": OncelikAjan,
}


def run_all_agents() -> dict:
    return {adi: sinif().calistir() for adi, sinif in _AJAN_KAYDEDICISI.items()}


def run_agent(ajan_adi: str) -> dict:
    sinif = _AJAN_KAYDEDICISI.get(ajan_adi)
    if sinif is None:
        gecerli = list(_AJAN_KAYDEDICISI.keys())
        raise ValueError(f"Bilinmeyen ajan: '{ajan_adi}'. Geçerli ajanlar: {gecerli}")
    return sinif().calistir()
