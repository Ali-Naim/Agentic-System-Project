# config.py
import os
from dotenv import load_dotenv # type: ignore

load_dotenv()

class Config:
    MOODLE_BASE_URL = os.getenv("MOODLE_BASE_URL")
    MOODLE_TOKEN = os.getenv("MOODLE_TOKEN")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    DATABASE_URL = os.getenv("DATABASE_URL")