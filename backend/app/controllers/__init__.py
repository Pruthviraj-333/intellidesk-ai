"""IntelliDesk AI — Controllers package."""

from .auth_controller import auth_bp
from .department_controller import department_bp, health_bp
from .user_controller import user_bp

__all__ = ["auth_bp", "user_bp", "department_bp", "health_bp"]
