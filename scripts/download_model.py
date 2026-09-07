"""
One-time model download script for METEORA NLP Embedding Engine.

Downloads paraphrase-multilingual-MiniLM-L12-v2 in ONNX format (~90MB)
and its tokenizer config from HuggingFace Hub.

Usage:
    uv run python scripts/download_model.py

Output:
    models/
      tokenizer.json          (~2MB  — HuggingFace tokenizer vocab)
      model.onnx              (~90MB — ONNX exported transformer)

The NLP extractor reads these files at startup automatically.
No GPU required. CPU inference only.
"""

import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

MODEL_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
ONNX_MODEL_ID = "onnx-community/paraphrase-multilingual-MiniLM-L12-v2-ONNX"
ONNX_FILENAME = "onnx/model.onnx"
MODELS_DIR = Path(__file__).parent.parent / "models"
TOKENIZER_PATH = MODELS_DIR / "tokenizer.json"
ONNX_PATH = MODELS_DIR / "model.onnx"


def download_tokenizer() -> None:
    """Download the HuggingFace tokenizer vocab (tokenizer.json)."""
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        logger.error("huggingface_hub not available. Run: uv add huggingface-hub")
        sys.exit(1)

    logger.info(f"Downloading tokenizer from {MODEL_ID} ...")
    path = hf_hub_download(
        repo_id=MODEL_ID,
        filename="tokenizer.json",
        local_dir=str(MODELS_DIR),
    )
    logger.info(f"  ✅ tokenizer.json → {path}")


def download_onnx_model() -> None:
    """Download the ONNX exported model weights (model.onnx)."""
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        logger.error("huggingface_hub not available. Run: uv add huggingface-hub")
        sys.exit(1)

    logger.info(f"Downloading ONNX model from {ONNX_MODEL_ID} (~90MB) ...")
    path = hf_hub_download(
        repo_id=ONNX_MODEL_ID,
        filename=ONNX_FILENAME,
        local_dir=str(MODELS_DIR),
        local_dir_use_symlinks=False,
    )
    # Copy from nested onnx/model.onnx to flat models/model.onnx
    import shutil

    dest = MODELS_DIR / "model.onnx"
    if Path(path) != dest:
        shutil.copy2(path, dest)
    logger.info(f"  \u2705 model.onnx \u2192 {dest}")


def main() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    if TOKENIZER_PATH.exists() and ONNX_PATH.exists():
        logger.info("✅ Models already present. Nothing to download.")
        logger.info(f"   tokenizer.json : {TOKENIZER_PATH} ({TOKENIZER_PATH.stat().st_size // 1024} KB)")
        logger.info(f"   model.onnx     : {ONNX_PATH} ({ONNX_PATH.stat().st_size // (1024 * 1024)} MB)")
        return

    if not TOKENIZER_PATH.exists():
        download_tokenizer()
    else:
        logger.info("  ⏭  tokenizer.json already exists, skipping.")

    if not ONNX_PATH.exists():
        download_onnx_model()
    else:
        logger.info("  ⏭  model.onnx already exists, skipping.")

    logger.info("")
    logger.info("✅ Download complete. METEORA will use real ONNX embeddings on next startup.")
    logger.info(f"   Set NLP_ONNX_MODEL_PATH={ONNX_PATH} in your .env (or it auto-detects from models/)")


if __name__ == "__main__":
    main()
