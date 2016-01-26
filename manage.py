import logging
from aio_manager import Manager
from eventsdisplay import settings
from eventsdisplay.app import build_application

logging.basicConfig(level=logging.WARNING)

app = build_application()
manager = Manager(app)

if __name__ == "__main__":
    manager.run()
