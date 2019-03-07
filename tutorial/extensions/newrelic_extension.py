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
