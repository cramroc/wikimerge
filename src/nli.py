# imports
from sentence_transformers import CrossEncoder

# NLI cross-encoder model (deberta-v3-xsmall: ~70 MB, CPU-friendly; no new heavy deps
# since sentence-transformers already pulls in transformers/torch for the embeddings)
NLI_MODEL = "cross-encoder/nli-deberta-v3-xsmall"

# model's label order (fixed by how it was trained; see the model card on HF)
NLI_LABELS = ["contradiction", "entailment", "neutral"]

# lazy singleton so the model is loaded once and reused (loading takes a few seconds)
_model = None
def get_model():
    global _model
    if _model is None:
        _model = CrossEncoder(NLI_MODEL)
    return _model

def classify_pair(premise, hypothesis):
    """
    Input:
        premise, hypothesis (str): the two English (translated) sentences to compare
    Output:
        str: the model's top label, one of "contradiction", "entailment", "neutral"
    """
    scores = get_model().predict([(premise, hypothesis)])[0]
    return NLI_LABELS[scores.argmax()]

def classify_bidirectional(text_a, text_b):
    """
    NLI is directional (premise -> hypothesis isn't symmetric), so check both
    orderings and fold them into a single verdict.
    Input:
        text_a, text_b (str): the two paragraphs to compare (order doesn't matter)
    Output:
        str: "contradiction" if either direction calls it a contradiction (a real
             contradiction is worse to miss than a false one is to show), else
             "entailment" if either direction agrees, else "neutral"
    """
    label_ab = classify_pair(text_a, text_b)
    label_ba = classify_pair(text_b, text_a)
    if "contradiction" in (label_ab, label_ba):
        return "contradiction"
    if "entailment" in (label_ab, label_ba):
        return "entailment"
    return "neutral"

# testing (run from project root: python -m src.nli)
if __name__ == "__main__":
    # one case per label, using translated-English-style sentences like the real pipeline
    cases = [
        ("agree (paraphrase)",
         "Cats are obligate carnivores and must eat meat.",
         "Cats are strict carnivores that require a meat-based diet."),
        ("contradiction (conflicting fact)",
         "The bridge was completed in 1932.",
         "The bridge was completed in 1965."),
        ("neutral (related but not a shared claim)",
         "The city has a population of two million people.",
         "The region experiences a Mediterranean climate."),
    ]

    for label, a, b in cases:
        result = classify_bidirectional(a, b)
        print(label + ": -> " + result)
