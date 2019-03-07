# nrscrapy

The New Relic Python agent does not support the Scrapy web scraping framework. This project shows a trivial example of how you can monitor your Scrapy application with New Relic by making use of the [Python Agent API](https://docs.newrelic.com/docs/agents/python-agent/python-agent-api). Consider the following example Spider:

``` python
import scrapy


class QuotesSpider(scrapy.Spider):
    name = "quotes"
    start_urls = [
        'http://quotes.toscrape.com/page/1/',
    ]

    def parse(self, response):
        for quote in response.css('div.quote'):
            yield {
                'text': quote.css('span.text::text').get(),
                'author': quote.css('small.author::text').get(),
                'tags': quote.css('div.tags a.tag::text').getall(),
            }

        for a in response.css('li.next a'):
            yield response.follow(a, callback=self.parse)
```

To monitor this Spider using New Relic, we just need to add three additional lines of code!

``` python

import newrelic.agent
newrelic.agent.initialize('newrelic.ini')

import scrapy


class QuotesSpider(scrapy.Spider):
    name = "quotes"
    start_urls = [
        'http://quotes.toscrape.com/page/1/',
    ]

    @newrelic.agent.background_task()
    def parse(self, response):
        for quote in response.css('div.quote'):
            yield {
                'text': quote.css('span.text::text').get(),
                'author': quote.css('small.author::text').get(),
                'tags': quote.css('div.tags a.tag::text').getall(),
            }

        for a in response.css('li.next a'):
            yield response.follow(a, callback=self.parse)

```

The `initialize` method is used to initialize the agent with your specified newrelic.ini configuration file.

The `@newrelic.agent.background_task()` decorator is used when you want to instrument background tasks or other non-web transactions. These transactions are displayed as non-web transactions in the APM UI and separated from web transactions.

## New Relic Extension Example

The extensions framework built into Scrapy provides a mechanism for inserting your own custom functionality into Scrapy. Extensions are just regular classes that are instantiated at Scrapy startup, when extensions are initialized. 

This project includes an example extension that collects some stats and records a New Relic Custom Event that can be queried using New Relic Insights.

``` python
import newrelic.agent

import logging
import datetime

from scrapy import signals
from scrapy.exceptions import NotConfigured

logger = logging.getLogger(__name__)


class NewRelic(object):

    def __init__(self):
        self.event_stats = {}

    @classmethod
    def from_crawler(cls, crawler):
        if not crawler.settings.getbool('MYEXT_ENABLED'):
            raise NotConfigured

        o = cls()
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(o.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(o.item_scraped, signal=signals.item_scraped)
        crawler.signals.connect(o.item_dropped, signal=signals.item_dropped)
        crawler.signals.connect(o.response_received, signal=signals.response_received)
        return o

    def set_value(self, key, value):
        self.event_stats[key] = value

    def spider_opened(self, spider):
        self.set_value('start_time', datetime.datetime.utcnow())

    def spider_closed(self, spider, reason):
        self.set_value('finish_time', datetime.datetime.utcnow())
        application = newrelic.agent.application()
        self.event_stats.update({'spider': spider.name})
        newrelic.agent.record_custom_event("ScrapyEvent", self.event_stats, application)

    def inc_value(self, key, count=1, start=0, spider=None):
        d = self.event_stats
        d[key] = d.setdefault(key, start) + count

    def item_scraped(self, item, spider):
        self.inc_value('item_scraped_count', spider=spider)

    def response_received(self, spider):
        self.inc_value('response_received_count', spider=spider)

    def item_dropped(self, item, spider, exception):
        reason = exception.__class__.__name__
        self.inc_value('item_dropped_count', spider=spider)
        self.inc_value('item_dropped_reasons_count/%s' % reason, spider=spider)
```

## Setup

1. Clone the repo.
2. Install the requirements. `pip install -r requirements.txt`
3. Update `newrelic.ini` with your license key.
4. Run `cd tutorial`
5. Run `scrapy crawl quotes`
