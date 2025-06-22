from pathlib import Path
from sentence_transformers import SentenceTransformer
from chromadb import PersistentClient
from tqdm import tqdm
import subprocess

# Persistent DB path and collection name
CHROMA_DIR = Path.home() / ".nash_chroma"
COLLECTION_NAME = "nash_file_index"
DOCUMENTS_DIR = Path.home() / "Documents/GitHub/nash/test"

# Embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# New Chroma persistent client
client = PersistentClient(path=str(CHROMA_DIR))
collection = client.get_or_create_collection(COLLECTION_NAME)

def index_files():
    """Index all eligible files in ~/Documents"""
    if not DOCUMENTS_DIR.exists():
        print(f"Documents folder not found: {DOCUMENTS_DIR}")
        return

    indexed_ids = set(collection.get()["ids"])
    all_files = list(DOCUMENTS_DIR.glob("**/*"))

    to_index = [
        path for path in all_files
        if path.is_file()
        and path.suffix.lower() in {".py", ".txt", ".md", ".sh", ".json", ".csv"}
        and str(path.resolve()) not in indexed_ids
        and path.stat().st_size < 1024 * 1024  # skip files > 1MB
    ]

    if not to_index:
        print("No new files to index.")
        return

    for path in tqdm(to_index, desc="Indexing files", unit="file"):
        try:
            content = path.read_text(errors="ignore")
            embedding = model.encode(content)
            collection.add(
                documents=[content],
                embeddings=[embedding],
                ids=[str(path.resolve())]
            )
        except Exception as e:
            print(f"Failed to index {path}: {e}")

    client.persist()


def retrieve_context(query, top_k=3):
    """Query Chroma and return top-matching file chunks"""
    embedding = model.encode(query)
    results = collection.query(query_embeddings=[embedding], n_results=top_k)
    return results.get("documents", [[]])[0]

def build_prompt_with_context(nl_query):
    chunks = retrieve_context(nl_query)
    context = "\n\n---\n\n".join(chunks)

    git_context = get_git_context()
    if git_context:
        context += f"\n\n[Git Context]\n{git_context}"

    system = {
        "role": "system",
        "content": (
            "You are a shell assistant. Based on the following local file contents and Git context, "
            "generate a relevant one-line bash command.\n\n"
            f"{context}"
        )
    }
    return [system, {"role": "user", "content": nl_query}]

def get_git_context():
    try:
        status = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, check=True)
        diff = subprocess.run(["git", "diff", "--cached"], capture_output=True, text=True, check=True)
        return f"Git status:\n{status.stdout.strip()}\n\nGit staged diff:\n{diff.stdout.strip()}"
    except subprocess.CalledProcessError:
        return ""
    except FileNotFoundError:
        return ""