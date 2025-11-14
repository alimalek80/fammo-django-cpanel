from django.apps import AppConfig


class VetsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'vets'

    def ready(self):
        # Import signals so Django registers them
        from . import signals  # noqa: F401
