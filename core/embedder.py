import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import os

# ── Config ──────────────────────────────────────────────
DATA_PATH       = "data/workers.json"
INDEX_PATH      = "embeddings/workers.faiss"
METADATA_PATH   = "embeddings/workers_meta.json"
MODEL_NAME      = "all-MiniLM-L6-v2"

def build_index():
    """
    Load workers, embed their skill_tags, save FAISS index + metadata.
    Run this once to generate the index. The API loads it at startup.
    """

    # 1. Load worker data
    with open(DATA_PATH, "r") as f:
        workers = json.load(f)

    print(f"Loaded {len(workers)} workers")

    # 2. Load the embedding model
    model = SentenceTransformer(MODEL_NAME)

    # 3. Create one text string per worker from their skill_tags
    skill_texts = [" ".join(w["skill_tags"]) for w in workers]
    print(f"Sample skill text: '{skill_texts[0]}'")

    # 4. Generate embeddings — each becomes a 384-dimension vector
    embeddings = model.encode(skill_texts, show_progress_bar=True)
    embeddings = np.array(embeddings).astype("float32")

    print(f"Embedding shape: {embeddings.shape}")  # (10, 384)

    # 5. Build FAISS index
    dimension = embeddings.shape[1]           # 384
    index = faiss.IndexFlatL2(dimension)      # L2 = Euclidean distance
    index.add(embeddings)

    print(f"FAISS index has {index.ntotal} vectors")

    # 6. Save index and metadata
    os.makedirs("embeddings", exist_ok=True)
    faiss.write_index(index, INDEX_PATH)

    with open(METADATA_PATH, "w") as f:
        json.dump(workers, f, indent=2)

    print(f"Saved index to {INDEX_PATH}")
    print(f"Saved metadata to {METADATA_PATH}")


if __name__ == "__main__":
    build_index()