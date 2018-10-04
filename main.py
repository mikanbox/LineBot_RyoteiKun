# -*- coding: utf-8 -*-
import sys
import urllib
import json
import os
import requests
import pulp
import re
import datetime
import random
import psycopg2
import lxml.html
from bs4 import BeautifulSoup
from flask_sqlalchemy import SQLAlchemy # 変更
from sqlalchemy import *
from sqlalchemy.orm import *


sys.path.append('./vendor')

from flask import Flask, request, abort, render_template

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


# DB設定
db_uri = "sqlite:///" + os.path.join(app.root_path, 'JouneySpot.db') # 追加
db_uri = os.environ.get('DATABASE_URL') or "sqlite:///" + os.path.join(app.root_path, 'JouneySpot.db')



app.config['SQLALCHEMY_DATABASE_URI'] = db_uri # 追加
db = SQLAlchemy(app) # 追加

ENGINE = create_engine(
    db_uri,
    encoding = "utf-8",
    echo=True # Trueだと実行のたびにSQLが出力される
)



# DBデータ定義
class Spot(db.Model):
    __tablename__ = "spots" # 追加
    id    = db.Column(db.Integer, primary_key=True,autoincrement=True) # 追加
    name  = db.Column(db.String(), nullable=False) # 追加
    score = db.Column(db.Float()) # 追加
    lat   = db.Column(db.Float()) # 追加
    lng   = db.Column(db.Float()) # 追加
    pref  = db.Column(db.String(), nullable=False) # 追加
    attribute  = db.Column(db.Integer()) # 追加


class SpotDist(db.Model):
    __tablename__ = "spotdistance" # 追加
    id    = db.Column(db.Integer, primary_key=True,autoincrement=True) # 追加
    id_from     = db.Column(db.Integer()) # 追加
    id_to       = db.Column(db.Integer()) # 追加
    distance    = db.Column(db.Float()) # 追加
    time        = db.Column(db.Float()) # 追加
    searchTime  = db.Column(db.Float()) # 追加


class Journey:
    step = 0
    # location = ['大阪城', '通天閣', '万博公園', 'スパワールド', '大阪大学', 'ポンポン山']  # 拠点名
    location = []
    locationValue = {}
    timeEdge = {}
    PointValue = {} # 実際はエッジの利益
    MaxTravelTime = 60 * 60 * 1
    StayTime = 3600
    StartTime = ""
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


def calcPath(location, e, c, time, stayTime=3600):
    # 最適化問題を解く
    problem = pulp.LpProblem('sample', pulp.LpMaximize)
    x = {}  # 空の辞書
    for i in location:
        for j in location:
            x[i, j] = pulp.LpVariable("x({:},{:})".format(i, j), 0, 1, pulp.LpInteger)
    y = {}  # 空の辞書
    for i in location:
        y[i] = pulp.LpVariable("y({:})".format(i), 0, 1, pulp.LpInteger)

    problem += pulp.lpSum(c[i, j] * x[i, j] for i in location for j in location), "TotalCost"

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
    print("Status", pulp.LpStatus[status])
    print(problem)
    print("Result")

    for i in Journey.location:
        for j in Journey.location:
            print(x[i, j], x[i, j].value())

    for i in Journey.location:
        print(y[i], y[i].value())

    return x, y


def CreateResult(route, point):
    for i in Journey.location:
        if (point[i].value() == 1):
            print(i)
    for i in Journey.location:
        for j in Journey.location:
            if (route[i, j].value() == 1):
                print(i + "  to  " + j)

    pointCount = 0
    for i in Journey.location:
        if (point[i].value() == 1):
            pointCount+=1
    if (pointCount <= 1):  # 旅程が建てられない場合
        message = []
        message.append("可能なプランがありません！")
        return message



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
    # message.append(Journey.StartTime)
    mes = ""
    for i in range(len(jouneylist)):
        mes += jouneylist[i] + "  滞在:" + str(Journey.StayTime / 60) + "分くらい\n"
        if (i < len(jouneylist) - 1):
            mes += " ↓  移動:" + str(int(jouneyTime[i] / 60)) + "分くらい\n"
    message.append(mes)
    # message.append(Journey.EndTime)

    return message


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

def InitDB():
    Spot.metadata.create_all(bind = ENGINE)
    SpotDist.metadata.create_all(bind = ENGINE)

# -------------------------------------------
# メインルーチン
# -------------------------------------------
def mainRoutine(event=0,time=0,pref='大阪'):
    Journey.MaxTravelTime = time
    # ----------------------------------------------------------
    #   DB初期化
    # ----------------------------------------------------------
    InitDB()
    # ----------------------------------------------------------
    #   DBから要素取得とソート,GoogleAPIで位置取得
    # ----------------------------------------------------------
    spots = db.session.query(Spot).filter(Spot.pref == pref).order_by('score')
    for spot in spots:
        if (spot.lat == None):
            print(spot.name)
            spot.lat, spot.lng = getPointFromGoogleAPI(spot.name)
            db.session.commit()
    # # ----------------------------------------------------------
    # # BaseQueryオブジェクトから別のオブジェクトへ変更
    # # ----------------------------------------------------------
    for spot in spots:
        if (spot.lat != None):
            Journey.location.append(spot.name)
            Journey.locationValue[spot.name] = spot.score

    Journey.location = random.sample(Journey.location,5)

    # # ----------------------------------------------------------
    # #   i-jパスの設定
    # # ----------------------------------------------------------
    for i in spots:
        if (i.name not in Journey.location ):
            continue
        for j in spots:
            if (j.name not in Journey.location ):
                continue
            if (j.name == i.name):
                continue

            if (db.session.query(SpotDist).filter(SpotDist.id_from == i.id).filter(SpotDist.id_to == j.id).count() > 0 ):
                r = db.session.query(SpotDist).filter(SpotDist.id_from == i.id).filter(SpotDist.id_to == j.id)
                Journey.timeEdge[i.name,j.name] = r.time
                Journey.timeEdge[j.name,i.name] = r.time
                print("Data is discovered")
                continue
            if (db.session.query(SpotDist).filter(SpotDist.id_from == j.id).filter(SpotDist.id_to == i.id).count() > 0 ):
                r = db.session.query(SpotDist).filter(SpotDist.id_from == i.id).filter(SpotDist.id_to == j.id)
                Journey.timeEdge[i.name,j.name] = r.time
                Journey.timeEdge[j.name,i.name] = r.time
                print("Data is discovered")
                continue
            # i-jパスがない時
            spotdist = SpotDist()
            spotdist.time = getPathromGoogleAPI([i.lat,i.lng],[j.lat,j.lng])
            spotdist.id_from = i.id
            spotdist.id_to   = j.id
            db.session.add(spotdist)
            db.session.commit()
            Journey.timeEdge[i.name,j.name] = spotdist.time
            Journey.timeEdge[j.name,i.name] = spotdist.time
            print("Call DirectionAPI : " + i.name +"-"+ j.name +"   time: " +str(spotdist.time) )

    # # ----------------------------------------------------------
    # #   i-jコストの設定
    # # ----------------------------------------------------------
    for i in Journey.location:
        for j in Journey.location:
            Journey.PointValue[i, j] = Journey.locationValue[i] + Journey.locationValue[j]
            Journey.PointValue[j, i] = Journey.PointValue[i, j]



    # # ----------------------------------------------------------
    # #   最適化問題の計算
    # # ----------------------------------------------------------
    route, point = calcPath(Journey.location, Journey.timeEdge,
                            Journey.PointValue, Journey.MaxTravelTime, Journey.StayTime)
    # # ----------------------------------------------------------
    # #   返送用メッセージを生成
    # # ----------------------------------------------------------
    message = CreateResult(route, point)

    # # ----------------------------------------------------------
    # #   返送用Line構造体を生成
    # # ----------------------------------------------------------
    txtarray = []
    for st in message:
        print(st)
        txtarray.append(TextSendMessage(text=st))

    print("sendMessage")
    if (event !=None):
            line_bot_api.reply_message(event.reply_token,txtarray)








# -------------------------------------------
# API
# -------------------------------------------
# 端末からのデータ受取時に呼ばれるコールバック
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
        Journey.MaxTravelTime = (dt2 - dt1).total_seconds()

        print(Journey.StartTime)
        print(Journey.EndTime)

        print("maxTime")
        print(Journey.MaxTravelTime)
        # calcFirstJourneyData(event)
        mainRoutine(event,"大阪")

    if (Journey.step == 2):
        Journey.StartTime = event.postback.params["time"]
        Journey.step = 3
        date_picker2 = TemplateSendMessage(
            alt_text='終了時間を設定',
            template=ButtonsTemplate(
                text='終了時間を設定'+str(Journey.step),
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

    if (text in "テスト起動"):
        mainRoutine(event,22800,"大阪")


    if (text in "旅行"):
        Journey.step = 1
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='どこに行きたいですか？'+str(Journey.step)))

    if (text in "大阪"):
        if (Journey.step == 1):
            Journey.step = 2
            date_picker1 = TemplateSendMessage(
                alt_text='開始時間を設定',
                template=ButtonsTemplate(
                    text='開始時間を設定'+str(Journey.step),
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
                TextSendMessage(text='行きたい場所を教えてください'+str(Journey.step)))





# -------------------------------------------
# バックエンド側API
# -------------------------------------------
@app.route("/")
def hello():
    return "Hello World!"

#公共クラウドシステムからデータ取得(未使用)
@app.route("/getJourney/")
def helloDB():
    janl = "山岳;遊ぶ"
    janl = urllib.parse.quote(janl)
    query = {'place': '大阪府',
                               'limit': 20}
    query = urllib.parse.urlencode(query)
    url = "https://www.chiikinogennki.soumu.go.jp/k-cloud-api/v001/kanko/"+janl+"/json?"+query
    print(url)
    s = requests.Session()
    s.headers.update({'Referer': 'www.monotalk.xyz/example'})
    r = s.get(url)
    jsonData = r.json()

    print(json.dumps(jsonData,ensure_ascii=False, indent=2))

    return json.dumps(jsonData,ensure_ascii=False, indent=2)

#じゃらんからリストスクレイピングしてくる
# 30秒のタイムアウトがある
@app.route("/getSpotFromJaran/")
def GetJaran():
    InitDB()
    headers = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:47.0) Gecko/20100101 Firefox/47.0",
    }

    for number in range(1,47):
        print(str(number))
        # number = 47
        url = "https://www.jalan.net/kankou/"+'{0:02d}'.format(number)+"0000/"

        request = urllib.request.Request(url=url, headers=headers)
        response = urllib.request.urlopen(request)
        doc = lxml.html.fromstring(response.read())

        prefName = doc.xpath('//*[@id="topicpath"]/ol/li[3]')
        spotName = doc.xpath('//*[@id="cassetteType"]/li/div/div[2]/p[1]/a')
        spotScore = doc.xpath('//*[@id="cassetteType"]/li/div/div[2]/div[3]/span[2]')

        pref =""
        for p in prefName:
            pref = p.text[:-3]
            print(pref)
        # DBに追加
        spots = list()
        for (s, sc) in zip(spotName, spotScore):
            if (db.session.query(Spot).filter(Spot.name == s.text).count() > 0):
                continue
            spot = Spot()
            spot.name =s.text
            spot.pref = pref
            spot.score = float(sc.text)
            spots.append(spot)
        db.session.add_all(spots)
        db.session.commit()


    # Userテーブルのnameカラムをすべて取得
    spots = db.session.query(Spot).all()
    for spot in spots:
        print(str(spot.id) + "   "+spot.name + "  " + str(spot.score) )


    return "jaran"

## テスト用API
@app.route("/testMain/")
def testmain():
    mainRoutine(event = None,time=22800)
    return "API is succeed"


@app.route("/getSpotDist/")
def testmain2():
    # Userテーブルのnameカラムをすべて取得
    spotds = db.session.query(SpotDist).all()
    for spot in spotds:
        print(str(spot.id_from) + " - "+str(spot.id_to) + "  " + str(spot.time) )
    return "end"




if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
