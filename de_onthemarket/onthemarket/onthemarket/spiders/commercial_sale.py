import scrapy
from scrapy.selector import Selector
from scrapy.crawler import CrawlerProcess
import json
import urllib
import datetime

class Commercial_sale(scrapy.Spider):

    name = "onthemarket"

    base_url = 'https://www.onthemarket.com/for-sale/property/'

    params = {
        "page" : '1',
        "radius" : "3.0"
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36'
    }

    current_page = 1

    postcodes = []

    def __init__(self):
        content = ''
        with open('dartford.json', 'r') as f:
            for char in f:
                content += char

        for item in json.loads(content):
            self.postcodes.append(item['postcode'])

    async def start(self):
        filename = './output/Commercial_sale_' + datetime.datetime.today().strftime('%Y-%m-%d-%H-%M') + '.jsonl'

        for postcode in self.postcodes:

            url = self.base_url + postcode.lower() + '/?' + urllib.parse.urlencode(self.params)

            yield scrapy.Request(
                url,
                headers=self.headers,
                meta={
                    "filename" : filename,
                    'current_page' : self.current_page,
                    'postcode' : postcode
                },
                callback=self.link_parse
            )

    def link_parse(self, response):

        filename = response.meta.get('filename')
        postcode = response.meta.get('postcode')

        for link in response.css('[data-component="price-title"] a::attr(href)').getall():
            yield response.follow(
                url=link,
                headers=self.headers,
                meta={
                    "filename" : filename,
                },
                callback=self.parse_property_page
            )

        # handle pagination :
        try:
            self.current_page += 1
            total_pages = max([
                int(num_pg)
                for num_pg in response.css("div.XHcfhz ul a::text").getall()
            ])
        except:
            total_pages = 1

        if self.current_page <= total_pages:
            self.params['page'] = self.current_page
            next_page_link = self.base_url + postcode.lower() + "/?" + urllib.parse.urlencode(self.params)
            yield scrapy.Request(
                url=next_page_link,
                headers=self.headers,
                meta={
                    "filename" : filename,
                    'postcode' : postcode
                },
                callback=self.link_parse
            )

    def parse_property_page(self, response):

        filename = response.meta.get('filename')
        postcode = response.meta.get('postcode')

        features = {
            "id": response.url.split('/')[-2],
            "url": response.url,
            "postcode": postcode,
            "title": response.css('[data-test="property-title"]::text')
                            .get()
                            .strip(),
            "address": response.xpath('//h1[@data-test="property-title"]/following-sibling::div/text()')
                                .get()
                                .strip(),
            "price": response.css('[data-test="property-price"]::text')
                        .get(),
            "views": '',
            "agent_name": response.css('[class="text-sm font-bold"]::text')
                                    .get(),
            "agent_phone": response.css('div.AAapZ7::text').get(),
            "image_urls": [
                image.split(' ')[-2] 
                for image in response.css('[data-component="hero-images"] img::attr(srcset)').getall()
            ]
        }

        try:
            features['views'] = response.css('span[class="font-semibold"]::text').get().split('+')[0]
        except:
            pass

    
        with open(filename, 'a') as f:
            f.write(json.dumps(features, indent=2) + '\n')

    def test(self):
        content = ''
        with open('dartford.json', 'r') as f:
            for char in f:
                content += char

        for item in json.loads(content):
            self.postcodes.append(item['postcode'])


if __name__ == '__main__':
    # run scraper
    process = CrawlerProcess()
    process.crawl(Commercial_sale)
    process.start()

    # Commercial_sale.test(Commercial_sale)
