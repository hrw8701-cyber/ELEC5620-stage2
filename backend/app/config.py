import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT.parent / '.env')
DATABASE_URL = os.environ.get('DATABASE_URL', '')
MODEL_BASE_URL = os.getenv('MODEL_BASE_URL', 'http://10.167.60.148:8000/v1')
MODEL_NAME = os.getenv('MODEL_NAME', 'campus-qwen')
MODEL_API_KEY = os.getenv('MODEL_API_KEY', '')
MODEL_MODE = os.getenv('MODEL_MODE', 'live')
DEMO_MODE = os.getenv('DEMO_MODE', 'false').lower() == 'true'
UPLOAD_DIR = Path(os.getenv('UPLOAD_DIR', str(ROOT.parent / '.runtime/uploads'))).resolve()
if MODEL_NAME != 'campus-qwen':
    raise RuntimeError('Only campus-qwen is permitted.')
if MODEL_MODE not in {'live', 'fixture'}:
    raise RuntimeError('MODEL_MODE must be live or fixture.')
if MODEL_MODE == 'fixture' and not DEMO_MODE:
    raise RuntimeError('Fixture mode is restricted to explicit demo/test runs.')
