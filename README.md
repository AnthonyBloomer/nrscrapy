# nrscrapy
An example of how to monitor your Scrapy app with the New Relic agent.

## Setup

1. Clone the repo.
2. Install the requirements. `pip install -r requirements.txt`
3. Update `newrelic.ini` with your license key.
4. Run `cd tutorial`
5. Run `scrapy crawl quotes`


## How it Works

The New Relic Python agent does not support the Scrapy web scraping framework. This project shows a trivial example of how you can monitor your Scrapy application making use of the [Python Agent API](https://docs.newrelic.com/docs/agents/python-agent/python-agent-api). 

Consider the following example:

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

To monitor this spider using New Relic, we just need to add three additional lines of code!

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


