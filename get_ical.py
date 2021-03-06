#!/usr/local/bin/python2.4

import lxml.html
import mechanize
import random
import time
from time import sleep

from icalendar import Calendar, Event
import datetime 
from icalendar import UTC

import config

# Wait a random amount of time between page visits?
SLEEP_BEFORE_REQUESTS = False #True

# Maximum wait time between page visits
MAX_WAIT_TIME = 11

# Maximum number of categories to visit
MAX_CATEGORIES = None

# Maximum number of events, per category, to scrape
MAX_EVENTS_PER_CATEGORY = None

def get_from_web(url):

    # Sleep before requests so we don't hit the server as much.
    if SLEEP_BEFORE_REQUESTS:
        random_number = random.random() * MAX_WAIT_TIME
        sleep(random_number)

    b = mechanize.Browser()
    b.addheaders = [("User-agent", "I'm trying to convert the philosophy dept. calendar into iCal. I won't hammer your servers, but I'll satisfy your filter, thus: pugoogle02bu.princeton.edu")]
    print "About to read", url
    b.open(url)
    return b.response().read()

# This URL contains a listing of events arranged into categories.  It looks
# like the best place to start crawling.
base_href = "http://philosophy.princeton.edu"
category_listing_page_url = "/index.php?option=com_jcalpro&extmode=cats"

events = []

def read_category_listing(base_href, url):
    cat_listing_url = base_href + url
    cat_listing_page = get_from_web(cat_listing_url)
    cat_listing_page_tree = lxml.html.document_fromstring(cat_listing_page)

    # Loop over the various categories of event
    category_links = cat_listing_page_tree.cssselect('a.cattitle')

    for cat_link in category_links[:MAX_CATEGORIES]:
        cat_page_url = base_href + cat_link.attrib['href']
        cat_page = get_from_web(cat_page_url)
        cat_page_tree = lxml.html.document_fromstring(cat_page)

        # Within each category of event, loop over the events
        event_links = cat_page_tree.cssselect('a.eventtitle')

        for event_link in event_links[:MAX_EVENTS_PER_CATEGORY]:
            event_page_url = base_href + event_link.attrib['href']
            read_event_page(event_page_url)

def read_event_page(url):
    event_page = get_from_web(url)
    event_page_tree = lxml.html.document_fromstring(event_page)

    # We will extract information about the event and put it here.
    event = {}

    # This will be useful along the way.
    def get_text_by_class(css_class):
        try:
            return event_page_tree.cssselect('.' + css_class)[0].text_content()
        except IndexError:
            return None

    event['title'] = get_text_by_class('eventtitle')
    event['date'] = get_text_by_class('date')

    # The description is a bit tricky....
    description = ""

    # Add the speaker's name if there is one.
    speaker = get_text_by_class('speaker')
    if speaker:
        description += "Speaker: %s\n" % speaker

    # Put everything answering to the name "event desc large" inside one
    # variable, separated by newlines. Try to remove extraneous whitespace.
    description_pieces = []
    for x in event_page_tree.cssselect('.eventdesclarge'):
        piece = x.text_content().strip()
        if piece:
            description_pieces.append(piece)

    # Tack the big variable onto the description
    description += "\n\n".join(description_pieces)

    # Add the category and URL
    event['description'] = "%s\n\nCategory: %s\nURL: %s" % (
            description,
            get_text_by_class('cattitle'),
            url
            )

    # Add to a growing list of dictionaries
    events.append(event)

# Scrape Princeton's page
read_category_listing(base_href, category_listing_page_url)

# To test locally, visit an event page, Save Page As >> somewhere on your disk.
# Then run something like this:
#read_event_page("file:///tmp/borges.html")

ical = open(config.ICAL_OUTPUT_FILE, 'w')

cal = Calendar()
cal.add('X-WR-CALNAME', 'Princeton Philosophy Events')

def to_datetime(string):
    # Thanks to Rod Hyde, who answered the question, "How do you convert a
    # python time.struct_time object into a datetime object?" at StackOverflow.
    # <http://stackoverflow.com/questions/1697815/how-do-you-convert-a-python-time-struct-time-object-into-a-datetime-object>

    struct = time.strptime(string, "%A, %B %d, %Y At %I:%M %p")
    timestamp = time.mktime(struct) # in seconds since the epoch

    # Problem: These times are in whatever timezone New Jersey is currently in.
    # One solution would be to take the datetime object (created below) and
    # tell it that it's in EST or EDT. But I don't know how to do that. So I'll
    # adopt the following hacky solution: Convert immediately to UTC.
    if time.daylight:
        timestamp = timestamp + 60*60*4
    else:
        timestamp = timestamp + 60*60*5
    datetime = datetime.datetime.fromtimestamp(timestamp)
    return 

for event_dict in events:
    event = Event()
    event.add('summary', event_dict['title'])
    start_time = to_datetime(event_dict['date'])
    event.add('dtstart', start_time)
    event.add('dtend', start_time + datetime.timedelta(hours=2))
    event.add('description', event_dict['description'])
    cal.add_component(event)

string = cal.as_string()

# Hack to make the ical validate
string = string.replace(';VALUE=DATE','')

ical.write(string)
ical.close()
