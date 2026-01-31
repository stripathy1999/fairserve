from pathlib import Path
import os

# Absolute path to the backend directory
BACKEND_DIR = Path(__file__).parent.parent.resolve()

# Absolute path to the project root (one level up from backend)
PROJECT_ROOT = BACKEND_DIR.parent.resolve()

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
QUEUE_DIR = DATA_DIR / "queue"
BUDGET_DIR = DATA_DIR / "budget"

# Frontend directory
FRONTEND_DIR = PROJECT_ROOT / "frontend"
