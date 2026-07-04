# imports
from sentence_transformers import SentenceTransformer, util

# embedding model (small, fast, CPU-friendly; built for symmetric semantic similarity)
EMBED_MODEL = "all-MiniLM-L6-v2"

# lazy singleton so the model is loaded once and reused (loading takes a few seconds)
_model = None
def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL)
    return _model

# embed a list of texts into vectors
def embed(texts):
    return get_model().encode(texts)

# cosine similarity matrix between two lists of texts (shape: len(texts_a) x len(texts_b))
def similarity_matrix(texts_a, texts_b):
    return util.cos_sim(embed(texts_a), embed(texts_b))
