#!/usr/bin/env python3
"""
Script to generate embeddings for all empresas in the database.
Run this once to initialize embeddings, and whenever you add new empresas.

Usage:
    python generate_embeddings.py
"""

import sys
from app.database import get_db
from app import semantic_search

def main():
    print("=" * 60)
    print("EMPRESA EMBEDDINGS GENERATOR")
    print("=" * 60)
    print()

    # Check if OPENAI_API_KEY is set
    import os
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable not set!")
        print("Please add it to your .env file:")
        print("  OPENAI_API_KEY=sk-...")
        sys.exit(1)

    print("Connecting to database...")
    db = next(get_db())

    print("Starting embedding generation...")
    print("(This may take a few minutes depending on dataset size)")
    print()

    try:
        count = semantic_search.embed_all_empresas(db, batch_size=20)

        print()
        print("=" * 60)
        if count > 0:
            print(f"SUCCESS! Generated embeddings for {count} empresas")
        else:
            print("All empresas already have embeddings!")
        print("=" * 60)

    except Exception as e:
        print()
        print("=" * 60)
        print(f"ERROR: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
