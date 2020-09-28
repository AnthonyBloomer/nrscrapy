# Monitoring Scrapy using the New Relic Python Agent API

[Scrapy](https://scrapy.org) is web scraping framework that is unsupported by the New Relic Python agent. We occasionally receive support tickets asking to help with instrumenting a Scrapy application. The response we give to our customers is that it is unsupported but they can use custom instrumentation to monitor their Scrapy application. Recently I worked on a project to learn more about the Scrapy framework and to demonstrate how a customer can monitor an unsupported framework such as Scrapy using the Python Agent API.

## Basic Instrumentation using Agent Background Tasks

A trivial example of how a customer can monitor their Scrapy application is to use the background task decorator with the New Relic Python agent API. Consider the following Spider that scrapes content from [Quotes to Scrape:](https://quotes.toscrape.com)

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


To add basic instrumentation using the New Relic Python agent, we just need to add three additional lines of code!

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

In the example above, the `initialize` method is used to initialize the agent with the specified newrelic.ini configuration file. The `@newrelic.agent.background_task()` decorator is used to instrument the parse function as a background task. This transaction is then displayed as a non-web transactions in the APM UI and separated from web transactions.

## Advanced Instrumentation using Scrapy Extensions

To go one step further with instrumenting Scrapy applications is to use [Scrapy Extensions](https://docs.scrapy.org/en/latest/topics/extensions.html). The extensions framework built into Scrapy provides a mechanism for inserting your own custom functionality into Scrapy. Extensions are just regular classes that are instantiated at Scrapy startup, when extensions are initialized.

I worked on an extension that collects some statistics and records a New Relic custom event that can be queried using New Relic Insights. Scrapy uses [signals](https://docs.scrapy.org/en/latest/topics/signals.html) to notify when certain events occur. You can catch some of those signals in your Scrapy application using a custom extension to perform tasks or extend Scrapy to add functionality not provided out of the box. 

In my custom New Relic extension, I gather some basic statistics when the Spider is opened, closed, scraped, etc. In the closed method, I send the gathered data using the `record_custom_event` API method.

You can find the custom extension below:

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

The above example includes only a few of the signal events available. For a full list of signals go to: [https://docs.scrapy.org/en/latest/topics/signals.html](https://docs.scrapy.org/en/latest/topics/signals.html) 

 
## Testing the Project

 
To try this project, follow these steps:

1. Clone the repo: `git clone https://github.com/AnthonyBloomer/nrscrapy.git`
2. Install the requirements. Run `pip install -r requirements.txt`
3. Update `newrelic.ini` with your license key or export your license key as an environment variable.
4. Run `cd tutorial`
5. Run `scrapy crawl quotes`
