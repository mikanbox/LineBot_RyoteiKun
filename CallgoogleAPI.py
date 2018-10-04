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



def getGoogleMapDirection(route):
    # Goolge Map Direction API トークン
    api_key = "AIzaSyD9PKwDNyYQep3mw2M_cwUmWU3Kl9iNhRM"
    # Google Maps Direction API URL
    url = "https://maps.googleapis.com/maps/api/directions/json"

    try:
        q = {
            'origin': route.src.position(),    # 出発地点
            'destination': route.dest.position(),  # 到着地点
            'travelMode': 'driving',  # トラベルモード
            'key': api_key
        }

        s = requests.Session()
        r = s.get(url, params=q)
        json_o = r.json()
        print(url)
        return json_o

    except Exception as e:
        raise e

def getPathromGoogleAPI(fromplace,toplace):


    src = MapCoordinate(fromplace[0], fromplace[1])
    dest = MapCoordinate(toplace[0], toplace[1])
    route = MapRoute(src, dest, MapRoute.mode_transit)


    direction_json = getGoogleMapDirection(route)
    duringtime = direction_json['routes'][0]['legs'][
        0]['duration']["value"]  # これで２点間を車移動したときの秒数が入る

    return duringtime


def getPointFromGoogleAPI(PlaceName):
    place_url = 'https://maps.googleapis.com/maps/api/place/textsearch/json'
    query = {'query': PlaceName,
            'language': 'ja',
            'key': 'AIzaSyD9PKwDNyYQep3mw2M_cwUmWU3Kl9iNhRM'}
    s = requests.Session()
    s.headers.update({'Referer': 'www.monotalk.xyz/example'})

    r = s.get(place_url, params=query)
    json_start = r.json()


    if (json_start['status'] == 'ZERO_RESULTS'):
        return None,None

    # print(json.dumps(json_start,ensure_ascii=False, indent=2))

    location = json_start["results"][0]["geometry"]["location"]
    return float(location["lat"]),float(location["lng"])
