import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.selector import Selector
import json
import datetime
import csv

class Airbnb(scrapy.Spider):

    name = 'airbnb'

    # headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36'
    }

    base_url = 'https://fr.airbnb.com/s/homes?refinement_paths%5B%5D=%2Fhomes&location_search=NEARBY&source=structured_search_input_header&flexible_trip_lengths%5B%5D=one_week&monthly_start_date=2026-09-01&monthly_length=3&monthly_end_date=2026-12-01&price_filter_input_type=2&channel=EXPLORE&pagination_search=true&price_filter_num_nights=5&center_lat=33.59&center_lng=-7.62&federated_search_session_id=fd29199f-40e3-4020-9942-0b0e75f286f8&cursor=eyJzZWN0aW9uX29mZnNldCI6MCwiaXRlbXNfb2Zmc2V0IjowLCJ2ZXJzaW9uIjoxfQ%3D%3D'

    current_page_cursor_index = 0

    async def start(self):

        filename = './output/AIRBNB_' + datetime.datetime.today().strftime('%Y-%m-%d-%H-%M') + '.csv'

        yield scrapy.Request(
            url = self.base_url,
            meta={
                'filename' : filename
            },
            callback=self.parse_links
        )


    def parse_links(self, response):

        filename = response.meta.get("filename")
        result = json.loads(response.css('[id="data-deferred-state-0"]::text').get().split('"results:"')[-1])

        data = result['niobeClientData'][0][-1]['data']['presentation']['staysSearch']
        Ids = [i['listingId'] for i in data['mapResults']['staysInViewport']]

        # mapSearchResults = data['results']['searchResults']

        for Id in Ids:
            link = 'https://fr.airbnb.com/rooms/' + Id
            # price_tag = mapSearchResults[index]['structuredDisplayPrice']['primaryLine']['accessibilityLabel']
            yield scrapy.Request(
                url=link,
                meta={
                    'filename' : filename,
                    # 'price_tag' : price_tag
                },
                callback=self.parse_listings
            )

        # handle pagination :

        try:
            paginationInfo = data['results']['paginationInfo']['pageCursors']
            pages_links = [self.base_url.split('cursor=')[0] + 'cursor=' + cursor 
                            for cursor in paginationInfo]
            total_pages = len(paginationInfo)
            self.current_page_cursor_index += 1
            
        except:
            total_pages = 1


        if self.current_page_cursor_index < total_pages:

            next_page = pages_links[self.current_page_cursor_index]

            yield scrapy.Request(
                url=next_page,
                meta={
                    'filename' : filename
                },
                callback=self.parse_links
            )

    def parse_listings(self, response):

        # price_tag = response.meta.get('price_tag')
        filename = response.meta.get('filename')

        json_data = json.loads(response.css('script#data-deferred-state-0::text').get())

        features = {
            "id" : response.url.split('?search_mode=')[0].split('/')[-1],
            "url" : response.url,
            # "price_tag" : price_tag
        }

        sections = json_data['niobeClientData'][0][1]['data']['presentation']['stayProductDetailPage']['sections']['sections']
        for section in sections:
            if section['sectionId'] == 'AVAILABILITY_CALENDAR_DEFAULT':
                features['title'] = section['section']['listingTitle']

            if section['sectionId'] == 'DESCRIPTION_MODAL':
                features['description'] = section['section']['items'][0]['html']['htmlText']

            data = json_data['niobeClientData'][0][1]['data']['node']['pdpPresentation']

        features['overview'] = data['overview']['title']
        features['items'] = data['overview']['items']

        amenities_group = data['amenities']['seeAllAmenitiesGroups']
        amenities = []
        for group in amenities_group:
            if group['title'] != 'Non inclus':
                amenities.append({
                    f'{group["title"]}' : [item['title'] for item in group['amenities'] if item['available'] == True],
                })

        features['amenities'] = amenities

        keys = features.keys()

        with open(filename, 'a', newline="", encoding="utf-8-sig") as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerow(features)



if __name__ == '__main__':
    # run scraper
    process = CrawlerProcess()
    process.crawl(Airbnb)
    process.start()
