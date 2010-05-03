#!/usr/local/bin/python2.5
import lxml.html
import mechanize
import random
from time import sleep

from icalendar import Calendar, Event
import datetime 
from icalendar import UTC

import config

MAX_WAIT_TIME = 11
SLEEP_BEFORE_REQUESTS = True

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
    for cat_link in category_links:
        cat_page_url = base_href + cat_link.attrib['href']
        cat_page = get_from_web(cat_page_url)
        cat_page_tree = lxml.html.document_fromstring(cat_page)

        # Within each category of event, loop over the events
        event_links = cat_page_tree.cssselect('a.eventtitle')
        for event_link in event_links[:80]:
            event_page_url = base_href + event_link.attrib['href']
            read_event_page(event_page_url)

def read_event_page(url):
    event_page = get_from_web(url)
    event_page_tree = lxml.html.document_fromstring(event_page)

    # Extract information about the event.
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

def to_datetime(string):
    return datetime.datetime.strptime(string, "%A, %B %d, %Y At %I:%M %p ")

for event_dict in events:
    event = Event()
    event.add('summary', event_dict['title'])
    start_time = to_datetime(event_dict['date'])
    event.add('dtstart', start_time)
    event.add('dtend', start_time + datetime.timedelta(hours=2))
    event.add('description', event_dict['description'])
    cal.add_component(event)

ical.write(cal.as_string())
ical.close()
