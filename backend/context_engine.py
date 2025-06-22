import os
import faiss
import numpy as np
from pathlib import Path
from hashlib import md5
import subprocess

import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FileChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if not event.is_directory:
            reindex_file(event.src_path)

    def on_created(self, event):
        if not event.is_directory:
            reindex_file(event.src_path)

def reindex_file(filepath):
    if any(part.startswith('.') for part in Path(filepath).parts):
        return
    if any(skip in filepath for skip in ["venv", "__pycache__", ".git", "site-packages"]):
        return
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        emb = dummy_embed(content)
        index.add(np.array([emb]))
        doc_map[len(doc_map)] = (filepath, content[:300])
    except Exception:
        pass  # silently skip unreadable or transient files


# Watch a directory in the background
def watch_directory(path="."):
    event_handler = FileChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    print("[watchdog] Watching for changes...")
    threading.Thread(target=observer.join, daemon=True).start()


# Placeholder — replace with proper embedder (e.g., OpenAI, BGE, or SentenceTransformer)
def dummy_embed(text):
    return np.random.randn(384).astype("float32")

# In-memory FAISS index — should be persisted eventually
index = faiss.IndexFlatL2(384)
doc_map = {}

def index_files(root=".", max_files=100):
    i = 0
    for path in Path(root).rglob("*.*"):
        if i >= max_files: break
        try:
            content = path.read_text()
            emb = dummy_embed(content)
            index.add(np.array([emb]))
            doc_map[len(doc_map)] = (str(path), content[:300])
            i += 1
        except Exception:
            continue

index_files()
watch_directory(".")

def get_git_status():
    try:
        return subprocess.run(["git", "status"], capture_output=True, text=True).stdout.strip()
    except:
        return ""

def retrieve_context(query):
    q_emb = dummy_embed(query)
    D, I = index.search(np.array([q_emb]), k=3)
    results = [f"{doc_map[i][0]}:\n{doc_map[i][1]}" for i in I[0] if i in doc_map]

    git_diff = get_git_diff()
    git_status = get_git_status()

    if git_diff:
        results.append("GIT DIFF:\n" + git_diff[:1000])
    if git_status:
        results.append("GIT STATUS:\n" + git_status)

    return "\n\n".join(results)

def get_git_diff():
    try:
        result = subprocess.run(["git", "diff"], capture_output=True, text=True)
        return result.stdout.strip()
    except Exception:
        return ""

