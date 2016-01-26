import asyncio

from aiohttp.web import Application

from eventsdisplay.client import EventsServiceAPI
from eventsdisplay.settings import EVENTS_SERVICE_URL, TEMPLATES_DIR, ASSETS_DIR, DEBUG

from eventsdisplay.views import index, event, archive, TemplateLoader


def build_application():
    loop = asyncio.get_event_loop()
    app = Application(loop=loop)
    loop.run_until_complete(setup_events(app))

    prefix = r''
    if DEBUG:
        prefix = r'/events'

    app.router.add_route('GET', prefix + r'/', index)
    app.router.add_route('GET', prefix + r'/page/{page:\d+}/', index)
    app.router.add_route('GET', prefix + r'/event/{event:\d+}/', event)
    app.router.add_route('GET', prefix + r'/archive/', archive)
    app.router.add_route('GET', prefix + r'/archive/page/{page:\d+}/', archive)
    app.router.add_static(prefix + r'/assets/', ASSETS_DIR)
    return app


if __name__ == "__main__":
    pass


async def setup_events(app):
    events_api = EventsServiceAPI(EVENTS_SERVICE_URL)
    app['events_api'] = events_api

    app['loader'] = TemplateLoader(TEMPLATES_DIR)