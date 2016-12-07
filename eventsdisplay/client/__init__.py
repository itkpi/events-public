import json
import aiohttp


class EventsServiceAPIError(Exception):
    def __init__(self, errors=None):
        if not errors:
            errors = []
        super().__init__()
        self.errors = errors

    def __str__(self):
        return '; '.join(self.errors)


class EventsServiceAPI:
    def __init__(self, url):
        self.url = url
        self.session = aiohttp.ClientSession()

    async def get_events(self, api_key, offset=0, count=10, sorting=None, query=None):
        if not sorting:
            sorting = ''
        if not query:
            query = ''
        params = {'count': count,
                  'offset': offset,
                  'order_by': sorting,
                  'query': query}
        url = '{}/events'.format(self.url, count, offset, sorting, query)
        async with self.session.get(url,
                                    headers={'Client-Key': api_key},
                                    params=params) as response:
            await self.process_errors(url, response)
            data = await response.json()
        data['events'] = [self.prepare_event(event) for event in data.pop('events')]
        return data

    async def get_event(self, api_key, id_):
        url = '{}/events/{}'.format(self.url, id_)
        async with self.session.get(url,
                                    headers={'Client-Key': api_key}) as response:
            await self.process_errors(url, response)
            data = await response.json()
        return self.prepare_event(data)

    async def process_errors(self, url, response):
        if response.status > 299:
            if response.status == 400:
                json = await response.json()
                raise EventsServiceAPIError(['{}: {} [api]'.format(k, v) for k, v in json.items()])
            raise EventsServiceAPIError(
                ['Events Service returned {} error by url {}'.format(response.status, url)]
            )

    def prepare_event(self, event):
        event['metainfo'] = json.loads(event.pop('metainfo'))
        return event
