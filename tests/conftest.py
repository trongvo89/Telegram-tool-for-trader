"""Ensure imports work and env vars are stubbed before any bot.* import."""
import os
import sys

os.environ.setdefault("BOT_TOKEN", "test:stub")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("TWELVEDATA_API_KEY", "")
os.environ.setdefault("HEALTH_PORT", "0")

# Ensure project root is on sys.path regardless of how pytest is invoked
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
