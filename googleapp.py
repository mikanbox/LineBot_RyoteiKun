import urllib
import json
import os
import requests

# 位置座標クラス
class MapCoordinate:
    def __init__(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude

    def position(self):
        return "{0},{1}".format(self.latitude, self.longitude)
# ルートクラス
class MapRoute:
    mode_driving = "driving"
    mode_walking = "walking"
    mode_bicycling = "bicycling"
    mode_transit = "transit"

    def __init__(self, src, dest, mode):
        self.src = src
        self.dest = dest
        self.mode = mode
        self.lang = "ja"
        self.units = "metric"
        self.region = "ja"

# Goolge Map Direction 取得
def getGoogleMapDirection(route):

    # Goolge Map Direction API トークン
    api_key = "AIzaSyD9PKwDNyYQep3mw2M_cwUmWU3Kl9iNhRM"
    # Google Maps Direction API URL
    url = "https://maps.googleapis.com/maps/api/directions/json"

    try:
        q={
         'origin': route.src.position(),    # 出発地点 
         'destination':route.dest.position(),           #到着地点 
         'travelMode':'driving',                #トラベルモード 
         'key':api_key
         };

        s = requests.Session()
        r = s.get(url, params=q)
        json_o = r.json()
        print(url)
        return json_o

    except Exception as e:
        raise e




def calc2PointTime(fromPlaceName, toPlaceName):
    place_url = 'https://maps.googleapis.com/maps/api/place/textsearch/json'
    start_place_query = {'query': fromPlaceName,
         'language': 'ja',
         'key': 'AIzaSyD9PKwDNyYQep3mw2M_cwUmWU3Kl9iNhRM'}
    destination_place_query = {'query': toPlaceName,
         'language': 'ja',
         'key': 'AIzaSyD9PKwDNyYQep3mw2M_cwUmWU3Kl9iNhRM'}

    s = requests.Session()
    s.headers.update({'Referer': 'www.monotalk.xyz/example'})


    r = s.get(place_url, params=start_place_query)
    json_start = r.json()
    r = s.get(place_url, params=destination_place_query)
    json_destionation = r.json()

    location = json_start["results"][0]["geometry"]["location"]
    src = MapCoordinate(location["lat"], location["lng"])
    location = json_destionation["results"][0]["geometry"]["location"]
    dest = MapCoordinate(location["lat"], location["lng"]) 
    route = MapRoute(src, dest, MapRoute.mode_transit)

    direction_json = getGoogleMapDirection(route)
    # print(json.dumps(direction_json, indent=2))
    duringtime = direction_json['routes'][0]['legs'][0]['duration']["value"]#これで２点間を車移動したときの秒数が入る

    return duringtime


# duringtime = calc2PointTime('大阪城', '通天閣')
# print(  str(duringtime) +" sec")


place_url = 'https://maps.googleapis.com/maps/api/place/textsearch/json'
start_place_query = {'query': '通天閣',
     'language': 'ja',
     'key': 'AIzaSyD9PKwDNyYQep3mw2M_cwUmWU3Kl9iNhRM'}

s = requests.Session()
s.headers.update({'Referer': 'www.monotalk.xyz/example'})
r = s.get(place_url, params=start_place_query)
json_start = r.json()

print(json.dumps(json_start, indent=2))


