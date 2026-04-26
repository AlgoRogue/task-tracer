from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from tasks import (
    gorev_ekle, gorev_tamamla, gorev_arsivle,
    gorev_aktife_al, gorev_sil, gorevleri_yukle, arsivi_yukle,
    bugunun_gorevleri, gecmis_gorevler, yaklasan_gorevler
)

app = FastAPI(title="Task Tracer API")


class GorevGirdisi(BaseModel):
    baslik: str
    oncelik: str = "normal"
    son_tarih: Optional[str] = None


@app.get("/gorevler")
def gorevleri_listele():
    return gorevleri_yukle()


@app.post("/gorevler", status_code=201)
def gorev_olustur(veri: GorevGirdisi):
    try:
        return gorev_ekle(veri.baslik, veri.oncelik, veri.son_tarih)
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


@app.delete("/gorevler/{gorev_id}")
def gorevi_sil(gorev_id: int):
    try:
        if not gorev_sil(gorev_id):
            raise HTTPException(status_code=404, detail="Görev bulunamadı")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


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
