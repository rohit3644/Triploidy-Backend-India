import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "triploidy.settings")
app = Celery("triploidy")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()