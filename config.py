from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DATABASE_DIR = BASE_DIR / "database"
DATABASE_DIR.mkdir(exist_ok=True)

DATABASE_URL = f"sqlite:///{DATABASE_DIR / 'skillswap.db'}"

APP_TITLE = "SkillSwap Campus"
APP_ICON = "🔄"
# WebRTC signaling server used for voice/video calls.
# Keep localhost for local development; change this when deployed.
CALL_SERVER_URL = "http://localhost:8000"
