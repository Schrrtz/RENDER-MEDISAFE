from django.apps import AppConfig


class MyappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myapp'
    def ready(self):
        # Import signal handlers to register them. Keeps activity logging in-memory (cache) without migrations.
        try:
            from .utils import activity_signals  # noqa: F401
        except Exception:
            # Avoid breaking app startup if signals fail to import
            pass
