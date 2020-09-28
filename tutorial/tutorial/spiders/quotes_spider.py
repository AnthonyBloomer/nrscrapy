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
