"""
SessionContext — hibrit kalıcılık.

  son_gorev_id    → SQLite, 24 saat TTL
  secili_gorev_id → bellek içi, oturum sonu silinir
  aktif_filtre    → bellek içi, oturum sonu silinir
  son_eylem       → bellek içi, oturum sonu silinir
  bugun / saat    → her seferinde hesaplanır, saklanmaz
"""
import tasks

_TTL_SAAT = 24
_ANAHTAR_SON_GOREV = "son_gorev_id"


class SessionContext:
    def __init__(self):
        self._bellek: dict = {}  # oturum sonu kaybolan alanlar

    # --- son_gorev_id (kalıcı, TTL'li) ---

    def son_gorev_id_al(self) -> int | None:
        deger = tasks.session_degeri_al(_ANAHTAR_SON_GOREV, ttl_saat=_TTL_SAAT)
        return deger

    def son_gorev_id_kaydet(self, gorev_id: int) -> None:
        tasks.session_degerini_kaydet(_ANAHTAR_SON_GOREV, gorev_id, oturum_mu=False)

    # --- bellek içi alanlar ---

    def secili_gorev_id_al(self) -> int | None:
        return self._bellek.get("secili_gorev_id")

    def secili_gorev_id_kaydet(self, gorev_id: int) -> None:
        self._bellek["secili_gorev_id"] = gorev_id

    def aktif_filtre_al(self) -> dict:
        return self._bellek.get("aktif_filtre", {})

    def aktif_filtre_kaydet(self, filtre: dict) -> None:
        self._bellek["aktif_filtre"] = filtre

    def son_eylem_al(self) -> str | None:
        return self._bellek.get("son_eylem")

    def son_eylem_kaydet(self, eylem: str) -> None:
        self._bellek["son_eylem"] = eylem

    # --- temizlik ---

    def oturumu_kapat(self) -> None:
        """Oturum sonunda çağrılır; ephemeral alanları siler."""
        self._bellek.clear()
        tasks.session_oturumu_temizle()
