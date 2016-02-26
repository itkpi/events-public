import os
import re

import datetime
import pybars
import trafaret as t
from aiohttp.web_reqrep import Response
from aiohttp.web import HTTPFound
from dateutil.parser import parse

from eventsdisplay.eventsmonkey import EventsMonkey
from eventsdisplay.settings import EVENTS_API_KEY, EVENTS_PER_PAGE, DEBUG, EVENTSMONKEY_TEAM, EVENTSMONKEY_URL

INCLUDE_COMMENT = re.compile(r"{{!<[ ]*([^}]+)}}")


def _asset(options, val, *args, **kwargs):
    prefix = r'/events'
    return prefix + "/assets/{}".format(val)

def _date(options, format, *args, **kwargs):
    if options['when_start']:
        dt = parse(options['when_start'])
    else:
        dt = datetime.datetime.now()

    date = format.replace("YYYY", str(dt.year))
    date = date.replace("DD", str(dt.day))
    date = date.replace("MMMM", str(dt.month))
    date = date.replace("MM", str(dt.month))
    return date

def _strftime(options, source, format, *args, **kwargs):
    dt = parse(options[source])
    return datetime.datetime.strftime(dt, format)

def _excerpt(options, words, *args, **kwargs):
    text = options["agenda"]
    text = re.sub('<[^<]+?>', ' ', text)
    if text:
        text = ' '.join(text.split()[:int(words)])
    return text


class TemplateLoader:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.compiler = pybars.Compiler()

    def get_template(self, name):
        template_source = open(os.path.join(self.base_dir, name + ".hbs"), 'r', encoding='utf8').read()
        template = self.compiler.compile(template_source)
        base_template = None
        first_line = template_source.split("\n")[0]
        if INCLUDE_COMMENT.match(first_line):
            base_name = INCLUDE_COMMENT.findall(first_line)[0]
            base_template, _ = self.get_template(base_name)
        return template, base_template

    def get_partials(self):
        partials = {}
        base_partials = os.path.join(self.base_dir, 'partials')
        for name in os.listdir(base_partials):
            filename = os.path.splitext(name)[0]
            template_source = open(os.path.join(base_partials, name), 'r', encoding='utf8').read()
            template = self.compiler.compile(template_source)
            partials[filename] = template
        return partials

    def helpers(self):
        return {"asset": _asset,
                "date": _date,
                "excerpt": _excerpt,
                "strftime": _strftime,
                }


async def make_template(request, template_name, context):
    l = request.app['loader']
    template, base_template = l.get_template(template_name)
    body = template(context, helpers=l.helpers(), partials=l.get_partials())
    if base_template:
        context['body'] = body
        html = base_template(context, helpers=l.helpers(), partials=l.get_partials()).encode()
    else:
        html = body.encode()
    return html


async def events_list(request, sorting, query):
    page = int(request.match_info.get('page', 1))
    offset = (page - 1) * EVENTS_PER_PAGE

    context = default_context()
    events = await request.app['events_api'].get_events(EVENTS_API_KEY, offset, EVENTS_PER_PAGE,
                                                        sorting=sorting,
                                                        query=query)
    context.update(events)
    context['page'] = events['offset'] // EVENTS_PER_PAGE + 1
    context['next_page'] = context['page'] + 1
    context['prev_page'] = context['page'] - 1
    return context


async def index(request):
    today = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d")
    query = "when_start >= '{}'".format(today)
    context = await events_list(request, 'when_start', query)
    html = await make_template(request, "events", context)
    return Response(body=html, headers={'Content-type': 'text/html; charset=utf-8'})


async def archive(request):
    today = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d")
    query = "when_start < '{}'".format(today)
    context = await events_list(request, '-when_start', query)
    context['archive'] = '/archive'
    html = await make_template(request, "events", context)
    return Response(body=html, headers={'Content-type': 'text/html; charset=utf-8'})


async def event(request):
    event_id = int(request.match_info['event'])
    event = await request.app['events_api'].get_event(EVENTS_API_KEY, event_id)

    context = default_context()
    context.update(event)

    html = await make_template(request, "event_page", context)
    return Response(body=html, headers={'Content-type': 'text/html; charset=utf-8'})


async def suggest(request):
    context = default_context()

    html = await make_template(request, "suggest_event", context)
    return Response(body=html, headers={'Content-type': 'text/html; charset=utf-8'})


EVENT_SUGGESTION_TRAFARET = t.Dict({
    'title': t.String,
    'agenda': t.String,
    'social': t.String(allow_blank=True),
    'place': t.String(allow_blank=True),
    'registration_url': t.URL(allow_blank=True) | t.Null,
    'image_url': t.URL(allow_blank=True) | t.String(max_length=0, allow_blank=True),
    'level': t.Enum('NONE', 'TRAINEE', 'JUNIOR', 'MIDDLE', 'SENIOR'),
    'when_start': t.String,
    'when_end': (t.String(allow_blank=True) >>
                 (lambda x: None if not x else x)) | t.Null,
    t.Key('include_time', to_name='only_date', default=False):
                                 t.StrBool >> (lambda x: not x),
    'submitter_email': t.Email(),
}).ignore_extra('submit')


async def suggest_save(request):
    context = default_context()

    data = await request.post()
    context.update(data)

    checked = None
    try:
        checked = EVENT_SUGGESTION_TRAFARET.check(data)
    except t.DataError as e:
        context['error'] = e.error
        print(e.error)
    print(checked)

    if checked:
        checked['team'] = EVENTSMONKEY_TEAM
        api = EventsMonkey(EVENTSMONKEY_URL)
        suggested = api.suggest(checked)
        return HTTPFound(request.app.router['edit_suggested'].url(parts={"secret": suggested['secret']}))

    for level in 'TRAINEE', 'JUNIOR', 'MIDDLE', 'SENIOR':
        context["is_{}".format(level)] = checked.get('level') == level

    html = await make_template(request, "suggest_event", context)
    return Response(body=html, headers={'Content-type': 'text/html; charset=utf-8'})


async def suggest_edit(request):
    secret = request.match_info['secret']

    context = default_context()

    api = EventsMonkey(EVENTSMONKEY_URL)
    data = api.get(secret)
    context.update(data)
    context['edit'] = "{}://{}".format(request.scheme, request.host, request.path_qs)

    for level in 'TRAINEE', 'JUNIOR', 'MIDDLE', 'SENIOR':
        context["is_{}".format(level)] = data.get('level') == level

    html = await make_template(request, "suggest_event", context)
    return Response(body=html, headers={'Content-type': 'text/html; charset=utf-8'})


async def suggest_edit_save(request):
    secret = request.match_info['secret']

    context = default_context()

    data = await request.post()
    context.update(data)
    context['edit'] = "{}://{}".format(request.scheme, request.host, request.path_qs)
    for level in 'TRAINEE', 'JUNIOR', 'MIDDLE', 'SENIOR':
        context["is_{}".format(level)] = data.get('level') == level

    checked = None
    try:
        checked = EVENT_SUGGESTION_TRAFARET.check(data)
    except t.DataError as e:
        context['error'] = [{"key": k, "error": str(v)} for k,v in e.error.items()]

    if checked:
        checked['team'] = EVENTSMONKEY_TEAM
        api = EventsMonkey(EVENTSMONKEY_URL)
        suggested = api.edit(secret, checked)
        return HTTPFound(request.app.router['edit_suggested'].url(parts={"secret": suggested['secret']}))

    html = await make_template(request, "suggest_event", context)
    return Response(body=html, headers={'Content-type': 'text/html; charset=utf-8'})

# p.s. I know, it's ugliest code I ever wrote, but I need to do it quickly


def default_context():
    context = {}
    context['events_site'] = 'yes'
    context['body_class'] = 'home-template'
    context['meta_title'] = 'Events@ІТ КПІ'
    return context
