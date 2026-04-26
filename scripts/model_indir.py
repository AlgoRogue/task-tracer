"""
Encoder modelini HuggingFace'den indirir ve models/encoder/ dizinine kaydeder.

Kullanım:
  python scripts/model_indir.py
  python scripts/model_indir.py --model sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
  python scripts/model_indir.py --hedef /opt/modeller/encoder

İndirme sonrası ENCODER_MODEL_YOLU ayarlamadan da çalışır:
  models/encoder/config.json mevcutsa nlp/model_ayar.py otomatik keşfeder.
"""
import argparse
import sys
from pathlib import Path

_VARSAYILAN_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_VARSAYILAN_HEDEF = Path(__file__).parent.parent / "models" / "encoder"


def indir(model_id: str, hedef: Path) -> None:
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print(
            "Hata: huggingface_hub kurulu değil.\n"
            "  pip install huggingface-hub",
            file=sys.stderr,
        )
        sys.exit(1)

    hedef.mkdir(parents=True, exist_ok=True)
    print(f"Model indiriliyor: {model_id}")
    print(f"Hedef dizin     : {hedef}")

    try:
        snapshot_download(
            repo_id=model_id,
            local_dir=str(hedef),
            local_dir_use_symlinks=False,
        )
    except Exception as exc:
        print(f"Hata: İndirme başarısız — {exc}", file=sys.stderr)
        sys.exit(1)

    config = hedef / "config.json"
    if config.exists():
        print(f"Başarılı. Model hazır: {hedef}")
        print("Kullanım için ENCODER_MODEL_YOLU ayarlamaya gerek yok;")
        print("nlp/model_ayar.py dizini otomatik keşfeder.")
    else:
        print(
            "Uyarı: İndirme tamamlandı ancak config.json bulunamadı. "
            "Model eksik olabilir.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Encoder modelini indir")
    parser.add_argument(
        "--model",
        default=_VARSAYILAN_MODEL,
        help=f"HuggingFace model ID (varsayılan: {_VARSAYILAN_MODEL})",
    )
    parser.add_argument(
        "--hedef",
        default=str(_VARSAYILAN_HEDEF),
        help=f"Kayıt dizini (varsayılan: {_VARSAYILAN_HEDEF})",
    )
    args = parser.parse_args()
    indir(args.model, Path(args.hedef))
