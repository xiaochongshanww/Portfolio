"""兼容入口：加载 data/processed 中的标准化 chunks 到 ChromaDB。"""
import json
import logging
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.pipeline.load_to_db import load_chunks_to_db
from src.pipeline.paths import DB_DIR, PROCESSED_DIR


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    chunk_files = sorted(Path(PROCESSED_DIR).glob("*_chunks.json"))
    chunks_by_file = {}
    for chunk_file in chunk_files:
        source_file = chunk_file.name.replace("_chunks.json", ".pdf")
        chunks_by_file[source_file] = json.loads(chunk_file.read_text(encoding="utf-8"))
    load_chunks_to_db(chunks_by_file, DB_DIR)


if __name__ == "__main__":
    main()
