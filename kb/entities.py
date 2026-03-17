"""Entity extraction using spaCy transformer pipeline."""
import spacy
from typing import List, Dict, Set
import config

# Lazy-loaded NLP model
_nlp = None


def get_nlp():
    """Get or initialize the spaCy NLP model."""
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_trf")
        except OSError:
            raise RuntimeError(
                "spaCy model 'en_core_web_trf' not found. "
                "Run: python -m spacy download en_core_web_trf"
            )
    return _nlp


def extract_entities(text: str) -> List[Dict]:
    """Extract named entities from text using transformer-based NER."""
    nlp = get_nlp()
    doc = nlp(text[:100000])  # Limit text length for performance
    
    entities = []
    seen: Set[str] = set()
    
    for ent in doc.ents:
        if ent.label_ in config.ENTITY_TYPES:
            key = f"{ent.text.lower()}:{ent.label_}"
            if key not in seen:
                seen.add(key)
                entities.append({
                    "text": ent.text,
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char
                })
    
    return entities


def extract_entities_batch(texts: List[str]) -> List[List[Dict]]:
    """Extract entities from multiple texts."""
    nlp = get_nlp()
    
    # Process in batches for efficiency
    results = []
    for doc in nlp.pipe(texts, batch_size=8):
        entities = []
        seen: Set[str] = set()
        
        for ent in doc.ents:
            if ent.label_ in config.ENTITY_TYPES:
                key = f"{ent.text.lower()}:{ent.label_}"
                if key not in seen:
                    seen.add(key)
                    entities.append({
                        "text": ent.text,
                        "label": ent.label_,
                        "start": ent.start_char,
                        "end": ent.end_char
                    })
        
        results.append(entities)
    
    return results


def get_entity_summary(entities: List[Dict]) -> Dict[str, List[str]]:
    """Get summary of entities grouped by type."""
    summary: Dict[str, List[str]] = {}
    for ent in entities:
        label = ent["label"]
        if label not in summary:
            summary[label] = []
        if ent["text"] not in summary[label]:
            summary[label].append(ent["text"])
    return summary
