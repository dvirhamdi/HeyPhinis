from googleplaces import GooglePlaces, types, lang
from keys import *
from requests import get
import json


class results:
    def __init__(self, r):
        self.results = r

    def get(self):
        return self.results

    def sort_by_rating(self):
        def rating(r):
            if r.rating == "N/A":
                return 0
            else:
                return r.rating
        self.results.sort(key=rating)
        return self.results

    def sort_by_name(self):
        self.results.sort(key=lambda r: r.name)
        return self.results

    def append(self, item):
        self.results.append(item)

    # def sort_by_distance(self):
    #     self.results.sort(key=lambda r: r.name)


class Result_man:
    def __init__(self, place_id, url, close_to, name, icon, rating, local_phone_number, website, open_periods):
        self.id = place_id
        self.name = name
        self.icon = icon
        self.url = url
        self.rating = float(rating) if rating else "N/A"
        # self.rating_count = rating[1]
        self.local_phone_number = local_phone_number
        self.website = website
        self.images = []
        self.vicinity = close_to
        self.open_periods = open_periods

        self.fix_open()

    def fix_open(self):
        days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        new = {}
        if not self.open_periods:
            return
        for period in self.open_periods:
            for time in period:

                index = period[time]["day"]

                correct_day = days[index]
                correct_time = period[time]["time"][:2] +":"+ period[time]["time"][2:]

                if time == "closed":
                    new[correct_day] = {"closed": correct_time, "open": None}
                else:
                    new[correct_day] = {"open": correct_time, "closed": None}

        self.open_periods = new

    def add_images(self, images):
        self.images.append(images)

    def to_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'icon': self.icon,
            'close_to': self.vicinity,
            'url': self.url,
            'rating': self.rating,
            'number': self.local_phone_number,
            'website': self.website,
            'open_periods': self.open_periods
        }


# 31.894756, 34.809322
class query:
    def __init__(self, loc, radius, min_rating, place_type):
        self.lat, self.lng = loc
        # self.lat_lng = {'lat': self.lat, 'lng': self.lng}
        self.radius = radius
        self.rating_min = min_rating
        self.results = results([])
        self.type = place_type

    def get_all_pages(self, limit):
        query_results, next_k = find_places((self.lat, self.lng), self.radius, place_type=self.type)
        while next_k:
            data = find_places((self.lat, self.lng), self.radius, page_token=next_k)
            r, next_k = data
            if r:
                query_results += r

        for place in query_results:
            try:
                name = place["name"]
                icon = place["icon"]
                place_id = place['place_id']
            except TypeError:
                print("\n\n\n\n")
                print(place)
                print("\n\n\n\n")
                continue

            try:
                local_phone_number = place["formatted_phone_number"]
            except KeyError:
                local_phone_number = None

            try:
                close_to = place["vicinity"]
            except KeyError:
                close_to = None

            try:
                rating = place["rating"]
            except KeyError:
                rating = "None"

            try:
                website = place["website"]
            except KeyError:
                website = None

            try:
                url = place["url"]
            except KeyError:
                url = None

            try:
                open_now = place["opening_hours"]["open_now"]
                periods = place["opening_hours"]["periods"]
            except:
                open_now = "opening_hours" not in place
                periods = None

            if open_now and len(self.results.get()) < limit:
                try:
                    if rating > self.rating_min:
                        self.results.append(
                            Result_man(place_id, url, close_to, name, icon, rating, local_phone_number, website, periods))
                except:
                    self.results.append(
                        Result_man(place_id, url, close_to, name, icon, None, local_phone_number, website, periods))


def find_places(loc=(31.894756, 34.809322), radius=2_000, place_type="park", page_token=None, APIKEY=locations_key):
    lat, lng = loc
    if page_token:
        url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?" \
              f"pagetoken={page_token}" \
              f"&key={APIKEY}" \
              f"&language=en"
    else:
        url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?" \
              f"&location={lat},{lng}" \
              f"&radius={radius}" \
              f"&type={place_type}" \
              f"&key={APIKEY}" \
              f"&language=en"

    response = get(url)
    res = json.loads(response.text)
    ids = [r["place_id"] for r in res["results"]]

    results = []
    for p_id in ids:
        response = get(f"https://maps.googleapis.com/maps/api/place/details/json?place_id={p_id}&fields=icon,place_id,name,opening_hours,rating,formatted_phone_number,vicinity,website,url&key={locations_key}")
        res = json.loads(response.text)
        results.append(res["result"])
    next_page_token = res.get("next_page_token", None)
    return results, next_page_token
