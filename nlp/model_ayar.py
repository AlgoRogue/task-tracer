"""
Encoder model yolunu otomatik keşfeder.

Öncelik sırası:
  1. ENCODER_MODEL_YOLU env var (tam yol veya HuggingFace model ID)
  2. Yerel dizin: models/encoder/ (config.json varsa geçerli model sayılır)
  3. Fallback: None → stub (n-gram) kullanılır
"""
import os
from pathlib import Path

_YEREL_MODEL_DIZINI = Path(__file__).parent.parent / "models" / "encoder"


def model_yolu_bul() -> "str | None":
    env = os.environ.get("ENCODER_MODEL_YOLU", "").strip()
    if env:
        return env
    if (_YEREL_MODEL_DIZINI / "config.json").exists():
        return str(_YEREL_MODEL_DIZINI)
    return None
