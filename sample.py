# -*- coding: utf-8 -*-
import sys
import urllib
import json
import os
import requests
import pulp


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

    locationValue={}
    locationValue[fromPlaceName] = json_start["results"][0]["rating"]
    print(locationValue[fromPlaceName])

    location = json_start["results"][0]["geometry"]["location"]
    src = MapCoordinate(location["lat"], location["lng"])
    location = json_destionation["results"][0]["geometry"]["location"]
    dest = MapCoordinate(location["lat"], location["lng"]) 
    route = MapRoute(src, dest, MapRoute.mode_transit)

    direction_json = getGoogleMapDirection(route)
    # print(json.dumps(direction_json, indent=2))
    duringtime = direction_json['routes'][0]['legs'][0]['duration']["value"]#これで２点間を車移動したときの秒数が入る

    return duringtime


def calcPath(location, e,c,time,stayTime=3600):
    # location = ['a','b','c','d','e']#拠点名
    # time = 2
    # e = {} # 空の辞書#各拠点間時間
    # c = {} # 空の辞書cost   #拠点のコスト
    # for i in location:
    #     for j in location:
    #         e[i,j] = 1
    #         c[i,j] = 1

    #最適化問題を解く
    problem = pulp.LpProblem('sample', pulp.LpMaximize)
    # xi 拠点に行くなら1
    # 0-1変数を宣言
    # 変数集合を表す辞書
    x = {} # 空の辞書
    for i in location:
        for j in location:
            x[i,j] = pulp.LpVariable("x({:},{:})".format(i,j), 0, 1, pulp.LpInteger)
    y = {} # 空の辞書
    for i in location:
        y[i] = pulp.LpVariable("y({:})".format(i), 0, 1, pulp.LpInteger)

    problem += pulp.lpSum(c[i,j] * x[i,j] for i in location for j in location), "TotalCost"

    #総合時間を計算
    problem += sum(x[i,j] for i in location for j in location) + sum(y[i]*stayTime for i in location)  <= time, "Constraint_leq"

    for i in location:
        for j in location:
            if i==j:
                problem += x[i,j]*2 <= 1, "Constraint_leq_{:}_{:}".format(i,j)
            continue;
            problem += sum(x[i,j]+x[j,i]) <= 1, "Constraint_leq_{:}_{:}".format(i,j)

    for i in location:
        problem += x[i,i] == 0, "Constraint_node_eq{:}".format(i)

    for i in location:
        problem += sum(x[i,j] + x[j,i] for j in location) <= 2, "Constraint_node_{:}".format(i)

    for i in location:
        problem += sum(x[i,j] for j in location) <= y[i], "Constraint_node_y_{:}".format(i)


    problem += sum(y[i] for i in location) - sum(x[i,j] for i in location for j in location) == 1, "Constraint_eq2"


    status = problem.solve()
    print ("Status", pulp.LpStatus[status])
    print (problem)
    print ("Result")

    for i in location:
        for j in location:
            print (x[i,j], x[i,j].value())

    for i in location:
        print (y[i], y[i].value())


    return x,y


location = ['大阪城','通天閣','万博公園','スパワールド','大阪大学']#拠点名

timeEdge = {}
PointValue ={}

#データのセット
for i in location:
    for j in location:
        if ((i,j) in timeEdge):
            continue
        # print(i +"  " + j)
        timeEdge[i,j] = calc2PointTime(i, j)
        timeEdge[j,i] = timeEdge[i,j]
        PointValue[i,j] = 2
        PointValue[j,i] = PointValue[i,j]
        print(i +" to " + j + "   " + str(timeEdge[i,j]))



MaxTravelTime = 60*60*3
route,point = calcPath(location, timeEdge, PointValue, MaxTravelTime,3600)

for i in location:
    if (point[i].value() == 1):
        print(i)
for i in location:
    for j in location:
        if (route[i,j].value() == 1):
            print(i + "  to  " + j)




edge = {}
for i in location:
    for j in location:
        edge[i,j] = 0
for i in location:
    for j in location:
        if (route[i,j].value() == 1):
            edge[i,j] = 1
            edge[j,i] = 1

count = {}
for i in location:
    count[i] = 0
for i in location:
    for j in location:
        if (edge[i,j] == 1):
            count[i] += 1
            count[j] += 1

startLocation = 0
LastLocation = 0

for i in location:
    if (count[i] == 2):
        startLocation = i
        LastLocation = i

jouneylist = []
jouneyTime = []
for s in range(len(location)):
    for j in location:
        if (edge[startLocation,j] == 1 and LastLocation != j):
            jouneyTime.append(timeEdge[startLocation,j])
            jouneylist.append(startLocation)
            LastLocation = startLocation
            startLocation = j
jouneylist.append(startLocation)





print(jouneylist)
print(jouneyTime)



message = []

# message.append("いちばんおすすめのプランはこうだよ！")
# mes = ""
# for i in range(len(jouneylist)):
#     mes += jouneylist[i]
#     if (i < len(jouneylist) -1 ):
#         mes += " ↓ "

# message.append(mes)


message.append("いちばんおすすめのプランはこうだよ！")
time =60
mes = ""
for i in range(len(jouneylist)):
    mes += jouneylist[i] + "  滞在:" + str(time) +"分くらい\n"
    if (i < len(jouneylist) -1 ):
        mes += " ↓  移動:" + str(int(jouneyTime[i]/60) )+  "分くらい\n"

message.append(mes)

for st in message:
    print(st)







