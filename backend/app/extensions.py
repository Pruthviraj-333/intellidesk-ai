"""
IntelliDesk AI — Flask Extensions
All extension instances created here and initialized in the app factory.
This avoids circular imports.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_marshmallow import Marshmallow
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from celery import Celery

# ─── Database ORM ───────────────────────────────────────────────────────────────
db = SQLAlchemy()

# ─── Database Migrations ─────────────────────────────────────────────────────────
migrate = Migrate()

# ─── JWT Authentication ──────────────────────────────────────────────────────────
jwt = JWTManager()

# ─── Serialization ───────────────────────────────────────────────────────────────
ma = Marshmallow()

# ─── CORS ────────────────────────────────────────────────────────────────────────
cors = CORS()

# ─── WebSockets ──────────────────────────────────────────────────────────────────
socketio = SocketIO()

# ─── Rate Limiting ───────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ─── Email ───────────────────────────────────────────────────────────────────────
mail = Mail()

# ─── Celery (initialized separately, not via Flask extension pattern) ─────────────
celery_app = Celery(__name__)
