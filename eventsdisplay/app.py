import asyncio

from aiohttp.web import Application

from eventsdisplay.client import EventsServiceAPI
from eventsdisplay.settings import EVENTS_SERVICE_URL, TEMPLATES_DIR, ASSETS_DIR

from eventsdisplay.views import index, event, TemplateLoader


def build_application():
    loop = asyncio.get_event_loop()
    app = Application(loop=loop)
    loop.run_until_complete(setup_events(app))
    app.router.add_route('GET', '/', index)
    app.router.add_route('GET', r'/page/{page:\d+}/', index)
    app.router.add_route('GET', r'/event/{event:\d+}/', event)
    app.router.add_static('/assets/', ASSETS_DIR)
    return app


if __name__ == "__main__":
    pass


async def setup_events(app):
    events_api = EventsServiceAPI(EVENTS_SERVICE_URL)
    app['events_api'] = events_api

    app['loader'] = TemplateLoader(TEMPLATES_DIR)