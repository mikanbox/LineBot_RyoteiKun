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

src = MapCoordinate(34.733165, 135.500214) # 新大阪駅
dest = MapCoordinate(34.686669, 135.519586) # 大阪府庁舎
route = MapRoute(src, dest, MapRoute.mode_transit)

direction_json = getGoogleMapDirection(route)


print(json.dumps(direction_json, indent=2))

