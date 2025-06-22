from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
from pathlib import Path
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import time
import ast

# ─── Embedding Model ─────────────────────────────────────────────
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# ─── FAISS Index ─────────────────────────────────────────────────
index = faiss.IndexFlatL2(384)
doc_map = {}

# ─── Embedding Function ──────────────────────────────────────────
def embed(text):
    return embedder.encode(text, convert_to_numpy=True).astype("float32")

# ─── Watchdog Event Handler ──────────────────────────────────────
class FileChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if not event.is_directory:
            reindex_file(event.src_path)

    def on_created(self, event):
        if not event.is_directory:
            reindex_file(event.src_path)

# ─── File Indexing Logic ─────────────────────────────────────────
def reindex_file(filepath):
    if any(part.startswith('.') for part in Path(filepath).parts):
        return
    if any(skip in filepath for skip in ["venv", "__pycache__", ".git", "site-packages"]):
        return
    try:
        with open(filepath, 'r', errors="ignore") as f:
            content = f.read()
        structural_summary = extract_dependencies(content)
        emb = embed(content + "\n" + structural_summary)
        index.add(np.array([emb]))
        doc_map[len(doc_map)] = (filepath, content[:500])
    except Exception:
        pass

def extract_dependencies(code):
    try:
        tree = ast.parse(code)
        imports = [node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)]
        functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        return f"Imports: {imports}\nFunctions: {functions}\nClasses: {classes}"
    except:
        return ""

def index_files(root=".", max_files=100):
    i = 0
    for path in Path(root).rglob("*.*"):
        if i >= max_files: break
        reindex_file(str(path))
        i += 1

def watch_directory(path="."):
    event_handler = FileChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    print("[watchdog] Watching for changes...")
    threading.Thread(target=observer.join, daemon=True).start()

# ─── Git Context Retrieval ───────────────────────────────────────
def get_git_diff_by_file():
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True
        )
        files = result.stdout.strip().splitlines()
        chunks = []
        for f in files:
            diff = subprocess.run(["git", "diff", "--cached", f], capture_output=True, text=True).stdout.strip()
            if diff:
                chunks.append(f"{f}:{diff[:1000]}")
        return "\n\n".join(chunks)
    except:
        return ""

def get_git_status():
    try:
        return subprocess.run(["git", "status"], capture_output=True, text=True).stdout.strip()
    except:
        return ""

# ─── Context Retrieval ───────────────────────────────────────────
def retrieve_context(query):
    q_emb = embed(query)
    D, I = index.search(np.array([q_emb]), k=3)

    context = []
    for i in I[0]:
        if i in doc_map:
            path, snippet = doc_map[i]
            context.append(f"{path}:{snippet}")

    git_diff = get_git_diff_by_file()
    git_status = get_git_status()
    if git_diff:
        context.append("GIT DIFF:\n" + git_diff)
    if git_status:
        context.append("GIT STATUS:\n" + git_status)

    return "\n\n".join(context)

# ─── Init ─────────────────────────────────────────────────────────
index_files()
watch_directory(".")