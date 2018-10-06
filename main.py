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
from linebot import (LineBotApi, WebhookHandler)
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    SourceUser, SourceGroup, SourceRoom,
    TemplateSendMessage, ConfirmTemplate, MessageAction,
    ButtonsTemplate, ImageCarouselTemplate, ImageCarouselColumn, URIAction,
    PostbackAction, DatetimePickerAction,
    CameraAction, CameraRollAction, LocationAction,
    CarouselTemplate, CarouselColumn, PostbackEvent,
    StickerMessage, StickerSendMessage, LocationMessage, LocationSendMessage,
    ImageMessage, VideoMessage, AudioMessage, FileMessage,
    UnfollowEvent, FollowEvent, JoinEvent, LeaveEvent, BeaconEvent,
    FlexSendMessage, BubbleContainer, ImageComponent, BoxComponent,
    TextComponent, SpacerComponent, IconComponent, ButtonComponent,
    SeparatorComponent, QuickReply, QuickReplyButton
)


from CallgoogleAPI import *
import APIkey

app = Flask(__name__)
line_bot_api = LineBotApi(APIkey.channel_access_token)
handler = WebhookHandler(APIkey.channel_secret)

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


Pref_List = ['北海道','青森','岩手','宮城','秋田','山形','福島','栃木','群馬','茨城','埼玉','千葉','東京','神奈川','山梨','長野','新潟','富山','石川','福井','静岡','岐阜','愛知','三重','滋賀','京都','大阪','兵庫','奈良','和歌山','鳥取','島根','岡山','広島','山口','徳島','香川','愛媛','高知','福岡','佐賀','長崎','熊本','大分','宮崎','鹿児島','沖縄']

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
    pref = ""
    # location = ['大阪城', '通天閣', '万博公園', 'スパワールド', '大阪大学', 'ポンポン山']  # 拠点名
    location = []
    locationValue = {}
    timeEdge = {}
    PointValue = {} # 実際はエッジの利益
    MaxTravelTime = 60 * 60 * 1
    StayTime = 3600
    StartTime = ""
    EndTime = ""
    NowState ='listen_word'


# #状態の定義
states=['listen_word', 'listen_pref_plan', 'listen_time_plan','exec_plan', 'listen_spot_register','exec_register']


# -------------------------------------------
# pilpを用いて数理最適化を行う
# -------------------------------------------
def calcPath(location, e, c, time, stayTime=3600):
    # 最適化問題を解く
    problem = pulp.LpProblem('sample', pulp.LpMaximize)

    # -------------------------------------------
    # 決定変数定義
    # -------------------------------------------   
    x = { (i, j) :pulp.LpVariable("x({:},{:})".format(i, j), 0, 1, pulp.LpInteger) for i in location for j in location}
    y = { i : pulp.LpVariable("y({:})".format(i), 0, 1, pulp.LpInteger) for i in location}

    # -------------------------------------------
    # 目的関数設定
    # -------------------------------------------   
    problem += pulp.lpSum(c[i, j] * x[i, j] for i in location for j in location), "TotalCost"

    # -------------------------------------------
    # 制約式
    # -------------------------------------------   
    problem += sum(x[i, j] for i in location for j in location) + \
        sum(y[i] * stayTime for i in location) <= time, "Constraint_leq"

    for i in location:
        for j in location:
            if i == j:
                problem += x[i, j] * 2 <= 1, "Constraint_leq_{:}_{:}".format(i, j)
            continue
            problem += sum(x[i, j] + x[j, i]) <= 1, "Constraint_leq_{:}_{:}".format(i, j)

    for i in location:
        problem += x[i, i] == 0, "Constraint_node_eq{:}".format(i)

    for i in location:
        problem += sum(x[i, j] + x[j, i] for j in location) <= 2, "Constraint_node_{:}".format(i)

    for i in location:
        problem += sum(x[i, j] for j in location) <= y[i], "Constraint_node_y_{:}".format(i)

    problem += sum(y[i] for i in location) - sum(x[i, j] for i in location for j in location) == 1, "Constraint_eq2"

    # -------------------------------------------
    # pulpを用いた求解
    # -------------------------------------------  

    status = problem.solve()
    # print("Status", pulp.LpStatus[status])
    # print(problem)
    # print("Result")

    # for i in Journey.location:
    #     for j in Journey.location:
    #         print(x[i, j], x[i, j].value())

    # for i in Journey.location:
    #     print(y[i], y[i].value())

    return x, y


# -------------------------------------------
# 計算結果を解析しテキストを生成:(routeはエッジ,ポイントは点)
# -------------------------------------------
def CreateResult(route, point):
    print("\n ノード \n")
    for i in Journey.location:
        if (point[i].value() == 1):
            print(i)
    print("\n パス \n")
    for i in Journey.location:
        for j in Journey.location:
            if (route[i, j].value() == 1):
                print(i + "  to  " + j)

    pointCount = 0
    for i in Journey.location:
        if (point[i].value() == 1):
            pointCount+=1

    # -------------------------------------------
    # 旅程が建てられないとき
    # -------------------------------------------    
    if (pointCount <= 1):  # 旅程が建てられない場合
        message = []
        message.append("可能なプランがありません！")
        return message


    # -------------------------------------------
    # edge初期化,代入(内包) key:value if for
    # -------------------------------------------   
    edge = { (i, j) :0 for i in Journey.location for j in Journey.location}
    for i in Journey.location:
        for j in Journey.location:
            if route[i, j].value() == 1:
                edge[i,j] = 1
                edge[j,i] = 1

    # -------------------------------------------
    # スタートの特定:[i-j]が端点ならcount=2
    # -------------------------------------------   
    count = {i:0 for i in Journey.location}
    for i in Journey.location:
        for j in Journey.location:
            if (edge[i, j] == 1):
                count[i] += 1
                count[j] += 1

    # -------------------------------------------
    # 全部回れちゃう場合に問題起きる →　定式化を改善する必要がるが、応急処置
    # -------------------------------------------  
    startLocation = 0
    LastLocation = 0
    for i in Journey.location:
        if (count[i] == 2):
            startLocation = i
            LastLocation = i
    if (startLocation ==0):
        startLocation = Journey.location[0]
        LastLocation = startLocation


    # -------------------------------------------
    # スタートより旅程リストを生成
    # -------------------------------------------   
    jouneylist = []
    jouneyTime = []
    count = 1;
    for s in range(len(Journey.location)):#スポットの回数やる（あってる？)
        for j in Journey.location:
            if (edge[startLocation, j] == 1 and LastLocation != j):#スタートからjが存在し,jは前にたどった点じゃないなら
                jouneyTime.append(Journey.timeEdge[startLocation, j])
                jouneylist.append(startLocation)

                LastLocation = startLocation
                startLocation = j
                count+=1
            if ( count >= len(Journey.location)):
                break
        if ( count >= len(Journey.location)):
            break


    jouneylist.append(startLocation)#最後に終点を追加


    # -------------------------------------------
    #文章設計
    # -------------------------------------------   
    message = []
    message.append("おすすめのプランはこうだよ！")
    # message.append(Journey.StartTime)
    mes = ""
    for i in range(len(jouneylist)):
        mes += "■"+jouneylist[i] + "\n滞在:" + str(Journey.StayTime / 60) + "分くらい\n"
        if (i < len(jouneylist) - 1):
            mes += "↓\n↓  移動:" + str(int(jouneyTime[i] / 60)) + "分くらい\n↓\n"
    message.append(mes)
    # message.append(Journey.EndTime)

    return message


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
            print(spot.name+" : 新規追加操作")
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
                for r_elements in r:
                    Journey.timeEdge[i.name,j.name] = r_elements.time
                    Journey.timeEdge[j.name,i.name] = r_elements.time
                    print("Data is discovered")
                continue

            if (db.session.query(SpotDist).filter(SpotDist.id_from == j.id).filter(SpotDist.id_to == i.id).count() > 0 ):
                r = db.session.query(SpotDist).filter(SpotDist.id_from == i.id).filter(SpotDist.id_to == j.id)
                for r_elements in r:
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

    Journey.NowState = 'listen_word'



def AddSpot(event=0,text=""):
    # 名前も受け取る？
    lat, lng = getPointFromGoogleAPI(spot.name)
    spotName = ""
    spotScore =0
    if (lat == None):
        return False

    if (db.session.query(Spot).filter(Spot.name == s.text).count() > 0):
        return False

    #もしgoogleで検索できたら,,,
    # DBに追加

    # spots = list()
    # for (s, sc) in zip(spotName, spotScore):
    #     spot = Spot()
    #     spot.name =s
    #     spot.pref = pref
    #     spot.score = float(sc.text)
    #     spots.append(spot)
    # db.session.add_all(spots)
    # db.session.commit()
    spot = Spot()
    spot.lat = lat
    spot.lng = lng
    spot.name = spotName
    spot.pref = pref
    spot.score = float(spotScore)
    db.session.add(spot)
    db.session.commit()

    line_bot_api.reply_message(event.reply_token,
        TextSendMessage(text='スポットを登録したよ！'))

    return True


# -------------------------------------------
# regexによる言語処理
# -------------------------------------------
def getJourney(text):
    pattern = r".*旅行.*"
    match = re.search(pattern, text)
    if not match:
        return False
    return True

def getPref(text):
    for p in Pref_List:
        # rをつけるとエスケープシーケンスが無向に
        pattern = r".*" + p + r".*"
        match = re.search(pattern, text)
        if match:
            return match.group() #テキスト(県名)を返す
    return False

# 何時から何時まで？
def getTime(text):
    Key = "[^#]##[^#]"
    match = re.search(Key, text)
    if not match:
        return False
    return True

def getStop(text):
    for p in ['やめる','やめた','終了','止める','止めた']:
        pattern = r".*" + p + r".*"
        match = re.search(pattern, text)
        if match:
            return True #テキスト(県名)を返す
    return False





# -------------------------------------------
# Line messaging API
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
    print("GetPostBackEvent\n\n\n\n")
    print(event)

    if (Journey.step == 3):
        Journey.EndTime = event.postback.params["time"]
        dt1 = datetime.datetime.strptime(Journey.StartTime, '%H:%M')
        input_time1 = dt1.time()
        dt2 = datetime.datetime.strptime(Journey.EndTime, '%H:%M')
        input_time2 = dt2.time()
        Journey.MaxTravelTime = (dt2 - dt1).total_seconds()        
        mainRoutine(event,32800,Journey.pref)

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
    print("GetTextMessage\n\n\n\n")
    print(Journey.NowState)
    text = event.message.text

    # -------------------------------------------
    # テスト用
    # -------------------------------------------
    if (text in "フレークサンプル"):
        sampleFlake(event)
        return True
    if (text in "テスト起動"):
        mainRoutine(event,22800,"大阪")
        return True





    # -------------------------------------------
    # 状態とテキストに応じて処理を記述
    # -------------------------------------------
    IsConversation = False
    if (Journey.NowState == 'listen_word'):
        if (getJourney(text)):
            Journey.NowState = 'listen_pref_plan'
        else:
            IsConversation = True
    # if () //スポット登録

    if (Journey.NowState == 'listen_pref_plan'):
        if (getPref(text)):
            Journey.pref = getPref(text)
            Journey.NowState = 'listen_time_plan'
    # やっぱやめる場合
    if (getStop(text)):
        Journey.NowState = 'listen_word'




    # -------------------------------------------
    # 状態に応じて返信メッセージを記述
    # -------------------------------------------
    if (Journey.NowState == 'listen_word'):
        # 雑談フラグ作って、それが1なら返す
        if IsConversation:
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text='なにがしたい〜？旅行って言ってくれたら計画立てるよ'))

    elif (Journey.NowState =='listen_pref_plan'):
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text='どの県にいきたい？'))

    elif (Journey.NowState =='listen_time_plan'):
        Journey.step = 2
        date_picker1 = TemplateSendMessage(
            alt_text='開始時間を設定',
            template=ButtonsTemplate(
                text='hh - mm',
                title='旅行開始時間を入力',
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



def sampleFlake(event):
    # bubble = BubbleContainer(
    #             direction='ltr',
    #             hero=ImageComponent(
    #                 url='https://example.com/cafe.jpg',
    #                 size='full',
    #                 aspect_ratio='20:13',
    #                 aspect_mode='cover',
    #                 action=URIAction(uri='http://example.com', label='label')
    #             ),
    #             body=BoxComponent(
    #                 layout='vertical',
    #                 contents=[
    #                     # title
    #                     TextComponent(text='Brown Cafe', weight='bold', size='xl'),
    #                     # review
    #                     BoxComponent(
    #                         layout='baseline',
    #                         margin='md',
    #                         contents=[
    #                             IconComponent(size='sm', url='https://example.com/gold_star.png'),
    #                             IconComponent(size='sm', url='https://example.com/grey_star.png'),
    #                             IconComponent(size='sm', url='https://example.com/gold_star.png'),
    #                             IconComponent(size='sm', url='https://example.com/gold_star.png'),
    #                             IconComponent(size='sm', url='https://example.com/grey_star.png'),
    #                             TextComponent(text='4.0', size='sm', color='#999999', margin='md',
    #                                           flex=0)
    #                         ]
    #                     ),
    #                     # info
    #                     BoxComponent(
    #                         layout='vertical',
    #                         margin='lg',
    #                         spacing='sm',
    #                         contents=[
    #                             BoxComponent(
    #                                 layout='baseline',
    #                                 spacing='sm',
    #                                 contents=[
    #                                     TextComponent(
    #                                         text='Place',
    #                                         color='#aaaaaa',
    #                                         size='sm',
    #                                         flex=1
    #                                     ),
    #                                     TextComponent(
    #                                         text='Shinjuku, Tokyo',
    #                                         wrap=True,
    #                                         color='#666666',
    #                                         size='sm',
    #                                         flex=5
    #                                     )
    #                                 ],
    #                             ),
    #                             BoxComponent(
    #                                 layout='baseline',
    #                                 spacing='sm',
    #                                 contents=[
    #                                     TextComponent(
    #                                         text='Time',
    #                                         color='#aaaaaa',
    #                                         size='sm',
    #                                         flex=1
    #                                     ),
    #                                     TextComponent(
    #                                         text="10:00 - 23:00",
    #                                         wrap=True,
    #                                         color='#666666',
    #                                         size='sm',
    #                                         flex=5,
    #                                     ),
    #                                 ],
    #                             ),
    #                         ],
    #                     )
    #                 ],
    #             ),
    #             footer=BoxComponent(
    #                 layout='vertical',
    #                 spacing='sm',
    #                 contents=[
    #                     # callAction, separator, websiteAction
    #                     SpacerComponent(size='sm'),
    #                     # callAction
    #                     ButtonComponent(
    #                         style='link',
    #                         height='sm',
    #                         action=URIAction(label='CALL', uri='tel:000000'),
    #                     ),
    #                     # separator
    #                     SeparatorComponent(),
    #                     # websiteAction
    #                     ButtonComponent(
    #                         style='link',
    #                         height='sm',
    #                         action=URIAction(label='WEBSITE', uri="https://example.com")
    #                     )
    #                 ]
    #             ),
    #         )
    headerImage = ImageComponent(# 画像ヘッダ
                    url='https://example.com/cafe.jpg',
                    size='full',
                    aspect_ratio='20:13',
                    aspect_mode='cover',
                )



    bubble = BubbleContainer(
                direction='ltr',
                hero=headerImage,
                body=BoxComponent(
                    layout='vertical',
                    contents=[
                        # title
                        TextComponent(text='Brown Cafe', weight='bold', size='xl'),
                        # # info
                        BoxComponent(
                            layout='vertical',
                            margin='lg',
                            spacing='sm',
                            contents=[
                                BoxComponent(
                                    layout='baseline',
                                    spacing='sm',
                                    contents=[
                                        TextComponent(
                                            text='Place',
                                            color='#aaaaaa',
                                            size='sm',
                                            flex=1
                                        ),
                                        TextComponent(
                                            text='万博公園',
                                            wrap=True,
                                            color='#666666',
                                            size='sm',
                                            flex=5
                                        )
                                    ],
                                ),
                                BoxComponent(
                                    layout='baseline',
                                    spacing='sm',
                                    contents=[
                                        TextComponent(
                                            text='Time',
                                            color='#aaaaaa',
                                            size='sm',
                                            flex=1
                                        ),
                                        TextComponent(
                                            text="10:00 - 23:00",
                                            wrap=True,
                                            color='#666666',
                                            size='sm',
                                            flex=5,
                                        ),
                                    ],
                                ),
                            ],
                        )



                    ],
                ),



            )


    message = FlexSendMessage(alt_text="hello", contents=bubble)
    line_bot_api.reply_message(
        event.reply_token,
        message
    )



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
        prefname2 = doc.xpath('//*[@id="contentsListHeader"]/div/h1')


        pref =""
        for p in prefname2:
            pref = p.text[:-7]
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

## テスト用API
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
