# Apify SDK - toolkit for building Apify Actors (Read more at https://docs.apify.com/sdk/python).
from apify import Actor
# Requests - library for making HTTP requests in Python (Read more at https://requests.readthedocs.io)
import requests
# Beautiful Soup - library for pulling data out of HTML and XML files (Read more at https://www.crummy.com/software/BeautifulSoup/bs4/doc)
from bs4 import BeautifulSoup
import urllib
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

async def main():
    async with Actor:
        # Structure of input is defined in input_schema.json
        actor_input = await Actor.get_input() or {}
        url = actor_input.get('url')
        location = actor_input.get('location')

        # Get location
        Actor.log.info('Get location for: ' + location)
        place_id = get_place_id(location)

        if place_id:
            lat, lng = get_lat_lng(place_id)
            print("Latitude:", lat)
            print("Longitude:", lng)
        else:
            Actor.log.info('Location coudn\'t be determined.')
            await Actor.exit()

        default_queue = await Actor.open_request_queue()
        page = 1
        url = get_url(lat, lng, page)
        await default_queue.add_request({ 'url': url, 'userData': { 'page': page }})

        while request := await default_queue.fetch_next_request():
            url = request['url']
            page = request['userData']['page']
            Actor.log.info(f'Scraping {url} ...')

            # Fetch the JSON content of the page.
            response = requests.get(url)
            if response.status_code == 200:
                json_response = response.json()
                data_list = json_response['data']
                Actor.log.info(f'Spotted {len(data_list)} data entries.')
                for data in data_list:
                    await Actor.push_data(data)

                next =  json_response['links']['next']
                if next is not None and next is not 'null':
                    page += 1
                    url = get_url(lat, lng, page)
                    await default_queue.add_request({ 'url': url, 'userData': { 'page': page }})
                
            else:
                Actor.log.info(f"Failed to fetch URL {url} with status code {response.status_code}")


def get_url(lat, lng, page=1, url_template="https://v3.nham24.com/api/v1/explore/store/1?page={page}&serviceId=1&sort=distance&latitude={lat}&longitude={lng}&per_page=30"):
    return url_template.format(lat=lat, lng=lng, page=page)

def get_place_id(search_term, url_template="https://v3.nham24.com/api/v1/explore/place/autocomplete?input={}"):
    # Encode the search term for URL
    encoded_search = urllib.parse.quote(search_term)

    # Call the URL with the search term
    url = url_template.format(encoded_search)
    response = requests.get(url)
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse JSON and extract the first result's place_id
        results = response.json()
        first_result = results[0]
        return first_result['place_id']
    else:
        print("Error:", response.status_code)
        return None

def get_lat_lng(place_id, url_template="https://v3.nham24.com/api/v1/explore/place/details?fields=formatted_address,geometry/location,name,place_id,type&place_id={}"):
    # Call the details URL with the place_id
    url = url_template.format(place_id)
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        details = response.json()
        location = details["geometry"]["location"]
        return location["lat"], location["lng"]
    else:
        print("Error:", response.status_code)
        return None, None
    