"""
Script to regenerate all embeddings using OpenAI's text-embedding-3-small model.
Run this after applying the migration to update vector dimensions.
"""
import os
import sys
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.app.database import SessionLocal
from backend.app.models import Empresa
from backend.app import embedding_service


def regenerate_all_embeddings(batch_size: int = 50):
    """
    Regenerate embeddings for all startups using OpenAI API.

    Args:
        batch_size: Number of records to commit at once
    """
    db = SessionLocal()

    try:
        # Get all empresas
        empresas = db.query(Empresa).all()
        total = len(empresas)

        if total == 0:
            print("No startups found in database.")
            return

        print(f"Regenerating embeddings for {total} startups using OpenAI text-embedding-3-small...")
        print(f"Estimated API calls: {total}")

        success_count = 0
        error_count = 0

        for i, empresa in enumerate(empresas, 1):
            try:
                # Generate new embedding using OpenAI
                vetor = embedding_service.generate_embedding(empresa)
                empresa.embedding_vector = vetor
                success_count += 1

                # Commit in batches
                if i % batch_size == 0:
                    db.commit()
                    print(f"Progress: {i}/{total} ({success_count} success, {error_count} errors)")

                # Rate limiting - OpenAI has limits
                time.sleep(0.1)  # 10 requests per second max

            except Exception as e:
                error_count += 1
                print(f"Error processing {empresa.nome_da_empresa}: {e}")
                continue

        # Final commit
        db.commit()
        print(f"\nCompleted: {success_count}/{total} embeddings generated ({error_count} errors)")

    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("OpenAI Embedding Regeneration Script")
    print("Model: text-embedding-3-small (1536 dimensions)")
    print("=" * 60)

    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable not set.")
        print("Set it with: export OPENAI_API_KEY=your-key-here")
        sys.exit(1)

    regenerate_all_embeddings()
