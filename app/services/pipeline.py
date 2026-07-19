from pathlib import Path
from uuid import uuid4
from app.services.embedder import embed_and_store
from app.services.loader import (
    extract_blocks,
    classify_document,
    build_hierarchy,
    prompt,
    structured_llm,
)

def make_collection_names(file_path: str):
    stem = Path(file_path).stem.replace(" ", "_").lower()

    return {
        "child": f"{stem}_child",
        "parent": f"{stem}_parent",
    }


def process_document(file_path: str | Path):
    print(f"Processing: {file_path}")

    collections = make_collection_names(file_path)
    
    blocks = extract_blocks(file_path)

    classifier = prompt | structured_llm
    result = classify_document(blocks, classifier)
    parents = build_hierarchy(blocks, result)

    embed_and_store(
        parents,
        child_collection_name=collections["child"],
        parent_collection_name=collections["parent"],
    )





    