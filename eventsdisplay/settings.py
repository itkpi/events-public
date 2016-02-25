import os

default_events_service = 'http://127.0.0.1:5000'
EVENTS_SERVICE_URL = os.environ.get('EVENTS_SERVICE_URL',
                                    default_events_service)

EVENTS_API_KEY = os.environ.get('EVENTS_API_KEY', "424242")

TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'theme'))
ASSETS_DIR = os.path.abspath(os.path.join(TEMPLATES_DIR, 'assets'))

EVENTS_PER_PAGE = 10
DEBUG = os.environ.get('DEBUG')
