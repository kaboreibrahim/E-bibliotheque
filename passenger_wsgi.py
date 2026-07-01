import os
import sys

# Absolute path to the project root (where this file lives)
PROJ_DIR = os.path.dirname(os.path.abspath(__file__))

# Make sure Django can find the project packages
if PROJ_DIR not in sys.path:
    sys.path.insert(0, PROJ_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
