import json
import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List
from tasks import (
    gorev_ekle, gorev_tamamla, gorev_arsivle,
    gorev_aktife_al, gorev_sil, gorev_duzenle,
    gorev_ara, etiketlere_gore_filtrele,
    gorevleri_yukle, arsivi_yukle,
    bugunun_gorevleri, gecmis_gorevler, yaklasan_gorevler,
    bildirimleri_yukle, bildirimi_goruldu_isaretle,
    gunluk_skor_getir, skor_gecmisini_getir,
    ajan_olaylarini_getir,
    desen_ekle, desen_onayla, desen_reddet, desen_bul,
)
from agents import run_all_agents, run_agent

app = FastAPI(title="Task Tracer API")

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=_TEMPLATES_DIR)


@app.get("/", response_class=HTMLResponse)
def anasayfa(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


class GorevGirdisi(BaseModel):
    baslik: str
    oncelik: str = "normal"
    son_tarih: Optional[str] = None
    etiketler: Optional[List[str]] = None


class GorevGuncelleme(BaseModel):
    baslik: Optional[str] = None
    oncelik: Optional[str] = None
    son_tarih: Optional[str] = None
    etiketler: Optional[List[str]] = None


@app.get("/gorevler")
def gorevleri_listele(etiket: Optional[str] = None):
    if etiket:
        return etiketlere_gore_filtrele(etiket)
    return gorevleri_yukle()


@app.post("/gorevler", status_code=201)
def gorev_olustur(veri: GorevGirdisi):
    try:
        return gorev_ekle(veri.baslik, veri.oncelik, veri.son_tarih, veri.etiketler)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.put("/gorevler/{gorev_id}/tamamla")
def gorevi_tamamla(gorev_id: int):
    if not gorev_tamamla(gorev_id):
        raise HTTPException(status_code=404, detail="Görev bulunamadı")
    return {"ok": True}


@app.put("/gorevler/{gorev_id}/arsivle")
def gorevi_arsivle(gorev_id: int):
    if not gorev_arsivle(gorev_id):
        raise HTTPException(status_code=404, detail="Görev bulunamadı")
    return {"ok": True}


@app.put("/gorevler/{gorev_id}/aktife-al")
def gorevi_aktife_al(gorev_id: int):
    if not gorev_aktife_al(gorev_id):
        raise HTTPException(status_code=404, detail="Görev bulunamadı")
    return {"ok": True}


@app.patch("/gorevler/{gorev_id}")
def gorevi_guncelle(gorev_id: int, veri: GorevGuncelleme):
    try:
        guncellendi = gorev_duzenle(gorev_id, veri.baslik, veri.oncelik, veri.son_tarih, veri.etiketler)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if guncellendi is None:
        raise HTTPException(status_code=404, detail="Görev bulunamadı")
    return guncellendi


@app.delete("/gorevler/{gorev_id}")
def gorevi_sil(gorev_id: int):
    try:
        if not gorev_sil(gorev_id):
            raise HTTPException(status_code=404, detail="Görev bulunamadı")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@app.get("/gorevler/ara")
def gorevleri_ara(q: Optional[str] = None, oncelik: Optional[str] = None, etiket: Optional[str] = None):
    return gorev_ara(q=q, oncelik=oncelik, etiket=etiket)


@app.get("/arsiv")
def arsivi_goruntule():
    return arsivi_yukle()


@app.get("/gorevler/bugun")
def bugun():
    return bugunun_gorevleri()


@app.get("/gorevler/gecmis")
def gecmis():
    return gecmis_gorevler()


@app.get("/gorevler/yaklasan")
def yaklasan(gun: int = 7):
    return yaklasan_gorevler(gun)


@app.get("/bildirimler")
def bildirimleri_getir(tur: Optional[str] = None, goruldu: Optional[int] = None):
    return bildirimleri_yukle(tur=tur, goruldu_mu=goruldu)


@app.put("/bildirimler/{bildirim_id}/goruldu")
def bildirimi_okundu_isaretle(bildirim_id: int):
    if not bildirimi_goruldu_isaretle(bildirim_id):
        raise HTTPException(status_code=404, detail="Bildirim bulunamadı")
    return {"ok": True}


@app.get("/skor")
def gunluk_skor(tarih: Optional[str] = None):
    skor = gunluk_skor_getir(tarih)
    if skor is None:
        from agents.skor import SkorAjan
        SkorAjan().calistir()
        skor = gunluk_skor_getir(tarih)
    return skor or {}


@app.get("/skor/gecmis")
def skor_gecmisi_getir(limit: int = 30):
    return skor_gecmisini_getir(limit=limit)


class AjanCalistirGirdisi(BaseModel):
    ajan: str = "hepsi"


@app.post("/ajanlar/calistir")
def ajanlari_calistir(veri: AjanCalistirGirdisi):
    try:
        if veri.ajan == "hepsi":
            return run_all_agents()
        return run_agent(veri.ajan)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/ajanlar/olaylar")
def ajan_olaylari_getir(ajan_adi: Optional[str] = None, limit: int = 50):
    return ajan_olaylarini_getir(ajan_adi=ajan_adi, limit=limit)


# --- NL pipeline ---

def _eylemi_uygula(yorum: dict):
    """Yorumdaki niyete göre görevi oluşturur veya durumunu değiştirir."""
    niyet = yorum.get("niyet")
    if niyet == "gorev_ekle":
        baslik = (yorum.get("baslik") or "").strip()
        if not baslik:
            return None
        etiketler = yorum.get("etiketler") or []
        return gorev_ekle(
            baslik,
            yorum.get("oncelik", "normal"),
            yorum.get("tarih"),
            etiketler if etiketler else None,
        )
    if niyet == "gorev_tamamla":
        hedef = yorum.get("hedef_id")
        if hedef:
            gorev_tamamla(hedef)
    elif niyet == "gorev_arsivle":
        hedef = yorum.get("hedef_id")
        if hedef:
            gorev_arsivle(hedef)
    return None


class NLGirdisi(BaseModel):
    girdi: str


class GeriBildirimGirdisi(BaseModel):
    desen_id: int
    onay: bool


@app.post("/nl/yorumla")
def nl_yorumla(veri: NLGirdisi):
    """
    Doğal dil girdisini yorumlar.
    - direkt_uygula: aksiyonu hemen çalıştırır
    - onay_iste: desen_id döner, /nl/geri-bildirim beklenir
    - acikla: kullanıcıdan netleştirme istenir
    """
    from agents.giris import GirisAjan
    karar = GirisAjan().yorumla_nl(veri.girdi)
    eylem = karar["eylem"]
    yorum = karar["yorum"]
    sonuc = {"eylem": eylem, "mesaj": karar.get("mesaj"), "yorum": yorum}

    if eylem == "direkt_uygula":
        gorev = _eylemi_uygula(yorum)
        if gorev:
            sonuc["gorev"] = gorev
        desen_id = yorum.get("_desen_id")
        if desen_id:
            desen_onayla(desen_id)

    elif eylem == "onay_iste":
        desen_id = yorum.get("_desen_id")
        if not desen_id:
            niyet_dict = {k: v for k, v in yorum.items() if not k.startswith("_")}
            desen_id = desen_ekle(veri.girdi, niyet_dict, guven=yorum.get("guven", 0.5))
        sonuc["desen_id"] = desen_id

    return sonuc


@app.post("/nl/geri-bildirim")
def nl_geri_bildirim(veri: GeriBildirimGirdisi):
    """Kullanıcının onay/red kararını desen hafızasına yazar ve aksiyonu çalıştırır."""
    if veri.onay:
        if not desen_onayla(veri.desen_id):
            raise HTTPException(status_code=404, detail="Desen bulunamadı")
        desen = desen_bul(veri.desen_id)
        if desen:
            niyet_dict = json.loads(desen["niyet"])
            gorev = _eylemi_uygula(niyet_dict)
            return {"ok": True, "gorev": gorev}
    else:
        if not desen_reddet(veri.desen_id):
            raise HTTPException(status_code=404, detail="Desen bulunamadı")
    return {"ok": True}
