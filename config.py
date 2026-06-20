import os

# MongoDB settings
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "talent_acquisition")

# LLM API settings
API_URL = os.getenv("API_URL", "http://llm01.cmi.rebhu.in:11434/api/chat")
# Default model name. The user can override this via environment variables or UI.
LLM_MODEL = os.getenv("LLM_MODEL", "gemma4:e2b") 

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JOB_ROLE_JSON_PATH = os.path.join(BASE_DIR, "job_role.json")
