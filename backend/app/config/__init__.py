"""IntelliDesk AI — Config package."""

from .settings import DevelopmentConfig, ProductionConfig, TestingConfig, config

__all__ = ["config", "DevelopmentConfig", "ProductionConfig", "TestingConfig"]
