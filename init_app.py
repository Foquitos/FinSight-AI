"""
FinSight AI — First-time setup script.

Run once after cloning the repository:
    python init_app.py

What it does:
  1. Checks Python version (3.10+)
  2. Creates a virtual environment (.venv/)
  3. Installs all dependencies from requirements.txt
  4. Creates the .env file with your Gemini API key
  5. Initialises the SQLite database and loads the CSV datasets
  6. Trains the fraud detection and purchase prediction ML models
  7. Builds the RAG vector index from the knowledge-base documents
  8. Prints the command to start the API server
"""

import os
import sys
import platform
import subprocess
import textwrap
import argparse

ROOT = os.path.dirname(os.path.abspath(__file__))

# ── Pretty-print helpers ───────────────────────────────────────────────────────

def _sep():
    print("-" * 62)

def header(text: str):
    print()
    _sep()
    print(f"  {text}")
    _sep()

def ok(text: str):    print(f"  [OK]  {text}")
def info(text: str):  print(f"  [ -> ] {text}")
def warn(text: str):  print(f"  [!]   {text}")
def fail(text: str):  print(f"  [ERR] {text}", file=sys.stderr)


# ── Step 1 — Python version ────────────────────────────────────────────────────

# Supported Python range. The upper bound matters: the heavy ML dependencies
# (pandas, numpy, scikit-learn, torch, chromadb) only publish pre-built wheels
# for released Python versions. On a newer, unsupported Python, pip falls back
# to compiling them from source, which needs a C/C++ toolchain (Visual Studio
# Build Tools on Windows) and almost always fails on a fresh machine.
MIN_PYTHON = (3, 10)
MAX_PYTHON = (3, 13)  # inclusive — newest version with wheels for all deps


def check_python():
    header("Step 1 · Checking Python version")
    v = sys.version_info
    current = f"{v.major}.{v.minor}.{v.micro}"

    if (v.major, v.minor) < MIN_PYTHON:
        fail(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required. Detected: {current}")
        sys.exit(1)

    if (v.major, v.minor) > MAX_PYTHON:
        fail(f"Unsupported Python version: {current}")
        fail(f"This project supports Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} "
             f"through {MAX_PYTHON[0]}.{MAX_PYTHON[1]} (3.12 recommended).")
        fail("Newer versions have no pre-built wheels for pandas/numpy/scikit-learn,")
        fail("so pip would compile them from source and fail without a C/C++")
        fail("compiler (Visual Studio Build Tools on Windows).")
        fail("Fix: install Python 3.12, delete the existing .venv/ folder, and")
        fail("re-run this script with that interpreter explicitly:")
        fail("  Windows:       py -3.12 init_app.py")
        fail("  Linux / macOS: python3.12 init_app.py")
        sys.exit(1)

    ok(f"Python {current}")


# ── Step 2 — Virtual environment ───────────────────────────────────────────────

def ensure_venv():
    header("Step 2 · Virtual environment")
    venv_dir = os.path.join(ROOT, ".venv")

    if os.path.isdir(venv_dir):
        ok("Virtual environment already exists (.venv/) — skipping creation.")
    else:
        info("Creating .venv/ ...")
        subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True, cwd=ROOT)
        ok("Virtual environment created.")

    is_windows = platform.system() == "Windows"
    python = os.path.join(venv_dir, "Scripts" if is_windows else "bin", "python" + (".exe" if is_windows else ""))
    pip    = os.path.join(venv_dir, "Scripts" if is_windows else "bin", "pip"    + (".exe" if is_windows else ""))

    if not os.path.isfile(python):
        fail(f"Could not find venv Python at: {python}")
        sys.exit(1)

    return python, pip


# ── Step 3 — Install dependencies ─────────────────────────────────────────────

def install_deps(pip: str):
    header("Step 3 · Installing dependencies")
    req = os.path.join(ROOT, "requirements.txt")
    if not os.path.isfile(req):
        fail("requirements.txt not found.")
        sys.exit(1)
    info("Running pip install — this can take several minutes on a fresh environment...")
    subprocess.run([pip, "install", "-r", req, "--quiet"], check=True, cwd=ROOT)
    ok("All dependencies installed.")


# ── Step 4 — .env file ────────────────────────────────────────────────────────

def setup_env():
    header("Step 4 · Environment configuration (.env)")
    env_path = os.path.join(ROOT, ".env")

    if os.path.isfile(env_path):
        ok(".env already exists — skipping.")
        return

    print()
    print("  FinSight AI uses Google Gemini as its LLM.")
    print("  Get a free API key at:  https://aistudio.google.com/app/apikey")
    print()

    api_key = input("  Enter your GEMINI_CHATBOT_API_KEY: ").strip()
    if not api_key:
        warn("No key entered. A placeholder will be written — edit .env before starting the server.")
        api_key = "your_gemini_api_key_here"

    with open(env_path, "w", encoding="utf-8") as f:
        f.write(f"GEMINI_CHATBOT_API_KEY={api_key}\n")

    ok(".env file created.")


# ── Step 5 — Datasets ─────────────────────────────────────────────────────────

def load_datasets(python: str):
    header("Step 5 · Loading CSV datasets into SQLite")

    fraud_csv    = os.path.join(ROOT, "data", "fraud_dataset.csv")
    purchase_csv = os.path.join(ROOT, "data", "product_purchase_dataset.csv")

    for path in [fraud_csv, purchase_csv]:
        if not os.path.isfile(path):
            fail(f"CSV not found: {path}")
            fail("Make sure the data/ folder contains both CSV files.")
            sys.exit(1)

    # Skip if tables already populated (database.db contains the transactions table)
    check_code = textwrap.dedent("""
        import sys, os
        sys.path.insert(0, sys.argv[1])
        os.chdir(sys.argv[1])
        from sqlalchemy import inspect
        from app.services.database.database import sqlite_engine
        tables = inspect(sqlite_engine).get_table_names()
        print("ok" if "transactions" in tables else "missing")
    """)
    result = subprocess.run(
        [python, "-c", check_code, ROOT],
        capture_output=True, text=True, cwd=ROOT
    )
    if result.stdout.strip() == "ok":
        ok("Tables already exist — skipping dataset load.")
        return

    info("Inserting data into SQLite...")
    result = subprocess.run(
        [python, os.path.join(ROOT, "data", "load_datasets.py")],
        capture_output=True, text=True, cwd=ROOT
    )
    if result.returncode != 0:
        fail("Dataset loading failed:")
        print(result.stderr)
        sys.exit(1)

    for line in result.stdout.strip().splitlines():
        info(line.strip())
    ok("Datasets loaded.")


# ── Step 6 — ML models ────────────────────────────────────────────────────────

# Inline training code executed in the venv Python.
# Uses dict() instead of {} literals to avoid brace-escaping in the string.
_TRAIN_CODE = textwrap.dedent("""
    import sys, os
    sys.path.insert(0, sys.argv[1])
    os.chdir(sys.argv[1])

    import joblib
    import pandas as pd
    from sklearn.model_selection import train_test_split, GridSearchCV
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.compose import ColumnTransformer
    from sklearn.preprocessing import StandardScaler, OneHotEncoder
    from sklearn.pipeline import Pipeline

    # Import from the proper module so joblib serialises them with the
    # correct fully-qualified path (not __main__).
    from app.services.ml.transformers import FraudFeatureEngineer, IncomeBracketParser

    os.makedirs("app/services/models", exist_ok=True)

    # ── Fraud detection model ──────────────────────────────────────────────────
    print("[1/2] Training fraud detection model (RandomForest + GridSearchCV)...")
    df = pd.read_csv("data/fraud_dataset.csv").drop(columns=["transaction_id", "customer_id"])
    X, y = df.drop(columns=["fraud"]), df["fraud"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    num_cols = X.select_dtypes(include=["int64", "float64"]).columns.tolist()
    num_cols += ["failed_velocity_ratio", "velocity_failure_index", "brute_force_warning"]
    cat_cols = X.select_dtypes(include=["object", "category"]).columns.tolist()

    pipeline = Pipeline([
        ("feature_engineer", FraudFeatureEngineer()),
        ("preprocessor", ColumnTransformer([
            ("num", StandardScaler(), num_cols),
            ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
        ])),
        ("classifier", RandomForestClassifier(random_state=42, class_weight="balanced")),
    ])
    gs = GridSearchCV(
        pipeline,
        dict(
            classifier__n_estimators=[50, 100],
            classifier__max_depth=[None, 5, 10],
            classifier__min_samples_split=[2, 5],
        ),
        cv=3, scoring="recall", n_jobs=-1, verbose=1,
    )
    gs.fit(X_train, y_train)
    joblib.dump(gs.best_estimator_, "app/services/models/fraud_pipeline.joblib")
    print("    Saved -> app/services/models/fraud_pipeline.joblib")

    # ── Purchase amount model ──────────────────────────────────────────────────
    print("[2/2] Training purchase amount model (RandomForest + GridSearchCV)...")
    df2 = pd.read_csv("data/product_purchase_dataset.csv")
    X2 = df2.drop(columns=["customer_id", "purchase_amount"])
    y2 = df2["purchase_amount"]
    X2_train, X2_test, y2_train, y2_test = train_test_split(X2, y2, test_size=0.2, random_state=42)

    cat_cols2 = [c for c in X2.select_dtypes(include=["object","category"]).columns if c != "income_bracket"]
    num_cols2  = X2.select_dtypes(include=["int64","float64"]).columns.tolist() + ["income_numeric"]

    pipeline2 = Pipeline([
        ("income_parser", IncomeBracketParser()),
        ("preprocessor", ColumnTransformer([
            ("num", StandardScaler(), num_cols2),
            ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols2),
        ])),
        ("regressor", RandomForestRegressor(random_state=42)),
    ])
    gs2 = GridSearchCV(
        pipeline2,
        dict(
            regressor__n_estimators=[50, 100, 200],
            regressor__max_depth=[None, 10, 20],
            regressor__min_samples_split=[2, 5],
            regressor__min_samples_leaf=[1, 2],
        ),
        cv=5, scoring="neg_mean_absolute_error", n_jobs=-1, verbose=1,
    )
    gs2.fit(X2_train, y2_train)
    joblib.dump(gs2.best_estimator_, "app/services/models/purchase_predictor.joblib")
    print("    Saved -> app/services/models/purchase_predictor.joblib")
    print("Models ready.")
""")


def train_models(python: str):
    header("Step 6 · Training ML models")

    fraud_path    = os.path.join(ROOT, "app", "services", "models", "fraud_pipeline.joblib")
    purchase_path = os.path.join(ROOT, "app", "services", "models", "purchase_predictor.joblib")

    if os.path.isfile(fraud_path) and os.path.isfile(purchase_path):
        ok("Model files already exist — skipping training.")
        return

    info("This may take 5–15 minutes depending on your machine...")
    result = subprocess.run([python, "-c", _TRAIN_CODE, ROOT], cwd=ROOT)
    if result.returncode != 0:
        fail("Model training failed. Check the output above for details.")
        sys.exit(1)
    ok("ML models trained and saved.")


# ── Step 7 — RAG vector index ─────────────────────────────────────────────────

_INDEX_CODE = textwrap.dedent("""
    import sys, os
    sys.path.insert(0, sys.argv[1])
    os.chdir(sys.argv[1])

    from app.config import settings          # initialises LlamaIndex Settings
    from app.services.database.database import sqlite_engine
    from app.services.Rag_llm.llm import finsight

    print("Building RAG vector index from documents in finsight_docs/ ...")
    print("(HuggingFace embedding model downloads ~90 MB on first run)")
    finsight(sql_engine=sqlite_engine, read_only=False)
    print("Index built and persisted.")
""")


def build_rag_index(python: str):
    header("Step 7 · Building RAG vector index")

    docstore = os.path.join(ROOT, "app", "services", "Rag_llm", "finsight_embeddings", "docstore.json")
    if os.path.isfile(docstore):
        ok("Vector index already exists — skipping.")
        return

    docs_dir = os.path.join(ROOT, "app", "services", "Rag_llm", "finsight_docs")
    md_files = [f for f in os.listdir(docs_dir) if f.endswith(".md")] if os.path.isdir(docs_dir) else []
    if not md_files:
        warn("No .md files found in finsight_docs/ — the index will be empty.")
        warn("Add your knowledge-base documents there and re-run this script.")
    else:
        info(f"Found {len(md_files)} document(s) in finsight_docs/")

    info("Embedding documents — requires internet access for the Gemini LLM init...")
    result = subprocess.run([python, "-c", _INDEX_CODE, ROOT], cwd=ROOT)
    if result.returncode != 0:
        fail("RAG index build failed. Check the output above.")
        fail("Tip: make sure your GEMINI_CHATBOT_API_KEY in .env is valid.")
        sys.exit(1)
    ok("Vector index built and persisted.")


# ── Done ───────────────────────────────────────────────────────────────────────

def print_summary():
    header("Setup complete!")
    activate = r".venv\Scripts\activate" if platform.system() == "Windows" else "source .venv/bin/activate"
    print(textwrap.dedent(f"""
      FinSight AI is ready to run.

      Start the API server:

        {activate}
        uvicorn app.main:app --reload

      Available endpoints  →  http://localhost:8000
        POST /api/v1/agent/chat               Financial agent (fraud + ML)
        POST /api/v1/chatbot/chat             RAG chatbot (streaming)
        GET  /api/v1/chatbot/history/{{user_id}}
        GET  /health
        GET  /docs                            Interactive API documentation
    """))


# ── Helpers for --step mode ────────────────────────────────────────────────────

def _get_venv_python():
    """Returns (python, pip) paths from the existing venv without creating it."""
    venv_dir = os.path.join(ROOT, ".venv")
    is_windows = platform.system() == "Windows"
    python = os.path.join(venv_dir, "Scripts" if is_windows else "bin", "python" + (".exe" if is_windows else ""))
    pip    = os.path.join(venv_dir, "Scripts" if is_windows else "bin", "pip"    + (".exe" if is_windows else ""))
    if not os.path.isfile(python):
        fail("Virtual environment not found at .venv/")
        fail("Run  python init_app.py  (without --step) to set it up first.")
        sys.exit(1)
    return python, pip


def _run_single_step(step: int):
    print()
    print("=" * 62)
    print(f"  FinSight AI — Step {step} only")
    print("=" * 62)

    if step == 1:
        check_python()
    elif step == 2:
        check_python()
        ensure_venv()
    elif step == 3:
        _, pip = _get_venv_python()
        install_deps(pip)
    elif step == 4:
        setup_env()
    elif step == 5:
        python, _ = _get_venv_python()
        load_datasets(python)
    elif step == 6:
        python, _ = _get_venv_python()
        train_models(python)
    elif step == 7:
        python, _ = _get_venv_python()
        build_rag_index(python)

    print()
    ok(f"Step {step} finished.")


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="FinSight AI — first-time setup script.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Steps:
              1  Check Python version
              2  Create virtual environment
              3  Install dependencies
              4  Configure .env (Gemini API key)
              5  Load CSV datasets into SQLite
              6  Train ML models
              7  Build RAG vector index

            Example — re-run only the training step after a failure:
              python init_app.py --step 6
        """),
    )
    parser.add_argument(
        "--step", type=int, choices=range(1, 8), metavar="N",
        help="Run only step N (1-7) instead of the full setup.",
    )
    args = parser.parse_args()

    if args.step:
        _run_single_step(args.step)
    else:
        print()
        print("=" * 62)
        print("  FinSight AI — First-time Setup")
        print("=" * 62)

        check_python()
        python, pip = ensure_venv()
        install_deps(pip)
        setup_env()
        load_datasets(python)
        train_models(python)
        build_rag_index(python)
        print_summary()
