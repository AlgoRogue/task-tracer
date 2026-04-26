"""
Bağlam çözücü — kural motorunun dolduramadığı referansları
SessionContext'ten tamamlar.
"""
from nlp.session_context import SessionContext


_HEDEF_GEREKTIREN = ("gorev_tamamla", "gorev_arsivle", "gorev_duzenle")


def coz(yorum: dict, context: SessionContext) -> dict:
    """
    Eksik hedef_id'yi bağlamdan tamamlar.
    Bağlamdan doldurulursa güvene +0.15 eklenir (max 0.90).
    """
    niyet = yorum.get("niyet", "")

    if niyet in _HEDEF_GEREKTIREN and yorum.get("hedef_id") is None:
        # Önce seçili görev (UI durumu), sonra son işlem yapılan
        hedef = context.secili_gorev_id_al() or context.son_gorev_id_al()
        if hedef is not None:
            mevcut_guven = yorum.get("guven", 0.5)
            return {
                **yorum,
                "hedef_id": hedef,
                "guven": min(round(mevcut_guven + 0.15, 4), 0.90),
            }

    return yorum
