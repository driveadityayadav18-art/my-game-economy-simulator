import sys
from pathlib import Path

# Ensure project root is in sys.path so 'src' can be imported in Vercel Lambda
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.main import app

# Export for Vercel WSGI / ASGI
handler = app
