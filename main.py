# -*- coding: utf-8 -*-
import sys
import urllib
import json
import os
import requests
import pulp
import re
import datetime
sys.path.append('./vendor')

from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    SourceUser, SourceGroup, SourceRoom,
    TemplateSendMessage, ConfirmTemplate, MessageTemplateAction,
    ButtonsTemplate, ImageCarouselTemplate, ImageCarouselColumn, URITemplateAction,
    PostbackTemplateAction, DatetimePickerTemplateAction,
    CarouselTemplate, CarouselColumn, PostbackEvent,
    StickerMessage, StickerSendMessage, LocationMessage, LocationSendMessage,
    ImageMessage, VideoMessage, AudioMessage, FileMessage,
    UnfollowEvent, FollowEvent, JoinEvent, LeaveEvent, BeaconEvent,
    ImageSendMessage
)


app = Flask(__name__)
line_bot_api = LineBotApi(
    "iGl4or4uXfRGwd9w0dk8UoDMDWn4z7KGtjSMC67WkwzJERiD+FLHwIkEhLeRCXLwuSg4MVuIvoVCDoxPjsJ9azXNe5MTPhPTWwBpf8e+1uuSW/FCL38Naqb0hehsaIqdoDApewB07WrdMuIR0bWMvQdB04t89/1O/w1cDnyilFU=")
handler = WebhookHandler('c9f4a586a8d8b03ce5f6008e79d1414e')


class Journey:
    step = 0
    location = ['大阪城', '通天閣', '万博公園', 'スパワールド', '大阪大学', 'ポンポン山']  # 拠点名
    locationValue = {}
    timeEdge = {}
    PointValue = {}
    MaxTravelTime = 60 * 60 * 1
    StayTime = 3600
    StartTime =""
    EndTime = ""



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

    Journey.locationValue[fromPlaceName] = json_start["results"][0]["rating"]

    location = json_start["results"][0]["geometry"]["location"]
    src = MapCoordinate(location["lat"], location["lng"])
    location = json_destionation["results"][0]["geometry"]["location"]
    dest = MapCoordinate(location["lat"], location["lng"])
    route = MapRoute(src, dest, MapRoute.mode_transit)



    direction_json = getGoogleMapDirection(route)
    duringtime = direction_json['routes'][0]['legs'][
        0]['duration']["value"]  # これで２点間を車移動したときの秒数が入る

    return duringtime


def calcPath(location, e, c, time, stayTime=3600):
    # location = ['a','b','c','d','e']#拠点名
    # time = 2
    # e = {} # 空の辞書#各拠点間時間
    # c = {} # 空の辞書cost   #拠点のコスト
    # for i in location:
    #     for j in location:
    #         e[i,j] = 1
    #         c[i,j] = 1

    # 最適化問題を解く
    problem = pulp.LpProblem('sample', pulp.LpMaximize)
    # xi 拠点に行くなら1
    # 0-1変数を宣言
    # 変数集合を表す辞書
    x = {}  # 空の辞書
    for i in location:
        for j in location:
            x[i, j] = pulp.LpVariable(
                "x({:},{:})".format(i, j), 0, 1, pulp.LpInteger)
    y = {}  # 空の辞書
    for i in location:
        y[i] = pulp.LpVariable("y({:})".format(i), 0, 1, pulp.LpInteger)

    problem += pulp.lpSum(c[i, j] x[i, j]
                          for i in location for j in location), "TotalCost"

    problem += sum(x[i, j] for i in location for j in location) + \
        sum(y[i] * stayTime for i in location) <= time, "Constraint_leq"

    for i in location:
        for j in location:
            if i == j:
                problem += x[i, j] * \
                    2 <= 1, "Constraint_leq_{:}_{:}".format(i, j)
            continue
            problem += sum(x[i, j] + x[j, i]
                           ) <= 1, "Constraint_leq_{:}_{:}".format(i, j)

    for i in location:
        problem += x[i, i] == 0, "Constraint_node_eq{:}".format(i)

    for i in location:
        problem += sum(x[i, j] + x[j, i]
                       for j in location) <= 2, "Constraint_node_{:}".format(i)

    for i in location:
        problem += sum(x[i, j]
                       for j in location) <= y[i], "Constraint_node_y_{:}".format(i)

    problem += sum(y[i] for i in location) - sum(x[i, j]
                                                 for i in location for j in location) == 1, "Constraint_eq2"

    status = problem.solve()
    print ("Status", pulp.LpStatus[status])
    print (problem)
    print ("Result")

    for i in Journey.location:
        for j in Journey.location:
            print (x[i,j], x[i,j].value())

    for i in Journey.location:
        print (y[i], y[i].value())

    return x, y


def CreateResult(route, point):
    for i in Journey.location:
        if (point[i].value() == 1):
            print(i)
    for i in Journey.location:
        for j in Journey.location:
            if (route[i,j].value() == 1):
                print(i + "  to  " + j)


    pointCount = 0
    # for i in Journey.location:
    #     if (point[i].value() == 1):
    #         pointCount+=1
    # if (pointCount <= 1):  # 旅程が建てられない場合
    #     return '可能なプランがありません！'

    edge = {}
    for i in Journey.location:
        for j in Journey.location:
            edge[i, j] = 0
    for i in Journey.location:
        for j in Journey.location:
            if (route[i, j].value() == 1):
                edge[i, j] = 1
                edge[j, i] = 1
    count = {}
    for i in Journey.location:
        count[i] = 0
    for i in Journey.location:
        for j in Journey.location:
            if (edge[i, j] == 1):
                count[i] += 1
                count[j] += 1

    startLocation = 0
    LastLocation = 0

    for i in Journey.location:
        if (count[i] == 2):
            startLocation = i
            LastLocation = i

    jouneylist = []
    jouneyTime = []
    for s in range(len(Journey.location)):
        for j in Journey.location:
            if (edge[startLocation, j] == 1 and LastLocation != j):
                jouneyTime.append(Journey.timeEdge[startLocation, j])
                jouneylist.append(startLocation)
                LastLocation = startLocation
                startLocation = j
    jouneylist.append(startLocation)

    print(jouneylist)
    print(jouneyTime)

    message = []

    message.append("いちばんおすすめのプランはこうだよ！")
    message.append(Journey.StartTime)
    mes = ""
    for i in range(len(jouneylist)):
        mes += jouneylist[i] + "  滞在:" + str(Journey.StayTime/60) + "分くらい\n"
        if (i < len(jouneylist) - 1):
            mes += " ↓  移動:" + str(int(jouneyTime[i] / 60)) + "分くらい\n"
    message.append(mes)
    message.append(Journey.EndTime)

    # for st in message:
    #     print(st)
    return message


def calcFirstJourneyData(event):

    for i in Journey.location:
        Journey.locationValue[i] = 0


    # データのセット
    for i in Journey.location:
        for j in Journey.location:
            if ((i, j) in Journey.timeEdge):
                continue
            Journey.timeEdge[i, j] = calc2PointTime(i, j)
            Journey.timeEdge[j, i] = Journey.timeEdge[i, j]
            Journey.PointValue[i, j] = Journey.locationValue[i] + Journey.locationValue[j]
            Journey.PointValue[j, i] = Journey.PointValue[i, j]
            print(i + " to " + j + "   " + str(Journey.timeEdge[i, j]))

    route, point = calcPath(Journey.location, Journey.timeEdge,
                            Journey.PointValue, Journey.MaxTravelTime, Journey.StayTime)

    message = CreateResult(route, point)


    txtarray =[]
    for st in message:
        print(st)
        txtarray.append(TextSendMessage(text=st))

    line_bot_api.reply_message(
        event.reply_token,
        txtarray)




@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(PostbackEvent)
def handle_postback(event):
    print(event)


    if (Journey.step == 3):

        Journey.EndTime = event.postback.params["time"]
        dt1 = datetime.datetime.strptime(Journey.StartTime, '%H:%M')
        input_time1 = dt1.time()
        dt2 = datetime.datetime.strptime(Journey.EndTime, '%H:%M')
        input_time2 = dt2.time()

        Journey.MaxTravelTime =  (dt2-dt1).total_seconds()

        print(Journey.StartTime)
        print(Journey.EndTime)

        print("maxTime")
        print(Journey.MaxTravelTime)
        calcFirstJourneyData(event)


    if (Journey.step == 2):
        Journey.StartTime = event.postback.params["time"]
        Journey.step = 3
        date_picker2 = TemplateSendMessage(
            alt_text='終了時間を設定',
            template=ButtonsTemplate(
                text='終了時間を設定',
                title='hh--mm',
                actions=[
                    DatetimePickerTemplateAction(
                        label='設定',
                        data='action=buy&itemid=2',
                        mode='time'
                    )
                ]
            )
        )
        line_bot_api.reply_message(
            event.reply_token,
            date_picker2
        )



@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text

    if (text in "旅行"):
        Journey.step = 1
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='どこに行きたいですか？'))

    if (text in "大阪"):
        if (Journey.step == 1):
            Journey.step = 2
            date_picker1 = TemplateSendMessage(
                alt_text='開始時間を設定',
                template=ButtonsTemplate(
                    text='開始時間を設定',
                    title='hh--mm',
                    actions=[
                        DatetimePickerTemplateAction(
                            label='設定',
                            data='action=buy&itemid=1',
                            mode='time'
                        )
                    ]
                )
            )
        line_bot_api.reply_message(
            event.reply_token,
            date_picker1
        )
    else:
        if (Journey.step == 1):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='行きたい場所を教えてください'))



# if __name__ == "__main__":
    # app.run(host='localhost', port=3000)
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

