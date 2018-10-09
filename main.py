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
    SeparatorComponent, QuickReply, QuickReplyButton,DatetimePickerTemplateAction
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

class UserState(db.Model):
    __tablename__ = "user_state" # 追加
    id    = db.Column(db.Integer, primary_key=True,autoincrement=True) # 追加
    user_id    = db.Column(db.String()) # 追加
    state      = db.Column(db.String()) # 追加
    pref = db.Column(db.String()) # 追加
    startTime = db.Column(db.String()) # 追加
    endTime = db.Column(db.String()) # 追加
    StayTime = db.Column(db.Integer(3600)) # 追加



class Journey:
    location = []
    locationValue = {}
    timeEdge = {}
    PointValue = {} # 実際はエッジの利益
    pref = ""
    MaxTravelTime = 60 * 60 * 1
    StayTime = 3600
    StartTime = ""
    EndTime = ""
    NowState = 'listen_word'


# #状態の定義
# states=['listen_word', 'listen_pref_plan', 'listen_time_plan','exec_plan', 'listen_spot_register','exec_register']


# -------------------------------------------
# pilpを用いて数理最適化を行う
# -------------------------------------------
def calcPath(location, e, c, time, stayTime):
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
    # 全体時間制約
    problem += sum(x[i, j] for i in location for j in location) + \
        sum(y[i] * stayTime for i in location) <= time, "Constraint_leq"

    # 単方向制約
    for i in location:
        for j in location:
            problem += sum(x[i, j] + x[j, i]) <= 1, "Constraint_leq_{:}_{:}".format(i, j)

    # 自身パス除去制約
    for i in location:
        problem += x[i, i] == 0, "Constraint_node_eq{:}".format(i)

    # 接続制約
    for i in location:
        problem += sum(sum(x[j, i] for j in location) - sum(x[i,k]  for k in location)) >= 0, "Constraint_node_{:}".format(i)


    # y起動制約
    for i in location:
        problem += sum(x[i, j] for j in location) <= y[i], "Constraint_node_y_{:}".format(i)
    for i in location:
        problem += sum(x[j, i] for j in location) <= y[i], "Constraint_node_y_r_{:}".format(i)


    # 部分巡回路除去制約
    problem += sum(y[i] for i in location) - sum(x[i, j] for i in location for j in location) == 1, "Constraint_eq2"

    # -------------------------------------------
    # pulpを用いた求解
    # -------------------------------------------  

    status = problem.solve()
    # print("Status", pulp.LpStatus[status])
    # print(problem)


    return x, y


# -------------------------------------------
# 計算結果を解析しテキストを生成:(routeはエッジ,ポイントは点)
# -------------------------------------------
def CreateResult(route, point,location,timeEdge):
    # print("\n ノード \n")
    # for i in Journey.location:
    #     if (point[i].value() == 1):
    #         print(i)

    # print("\n パス \n")
    # for i in Journey.location:
    #     for j in Journey.location:
    #         if (route[i, j].value() == 1):
    #             print(i + "  to  " + j)

    pointCount = 0
    for i in location:
        if (point[i].value() == 1):
            pointCount+=1

    # -------------------------------------------
    # 旅程が建てられないとき
    # -------------------------------------------    
    if (pointCount <= 1):  # 旅程が建てられない場合
        return None,None


    # -------------------------------------------
    # edge初期化,代入(内包) key:value if for
    # -------------------------------------------   
    edge = { (i, j) :0 for i in location for j in location}
    for i in location:
        for j in location:
            if route[i, j].value() == 1:
                edge[i,j] = edge[j,i] = 1

    # -------------------------------------------
    # スタートの特定:[i-j]が端点ならcount=2
    # -------------------------------------------   
    count = {i:0 for i in location}
    for i in location:
        for j in location:
            if (edge[i, j] == 1):
                count[i] += 1
                count[j] += 1

    # -------------------------------------------
    # 全部回れちゃう場合に問題起きる →　定式化を改善する必要がるが、応急処置
    # -------------------------------------------  
    startLocation = LastLocation  = 0
    for i in location:
        if (count[i] == 2):
            startLocation = LastLocation = i
    if (startLocation ==0):
        startLocation = location[0]
        LastLocation = startLocation


    # -------------------------------------------
    # スタートより旅程リストを生成
    # -------------------------------------------   
    jouneylist = []
    jouneyTime = []
    count = 1;
    for s in range(len(location)):#スポットの回数やる（あってる？)
        for j in location:
            if (edge[startLocation, j] == 1 and LastLocation != j):#スタートからjが存在し,jは前にたどった点じゃないなら
                jouneyTime.append(timeEdge[startLocation, j])
                jouneylist.append(startLocation)

                LastLocation = startLocation
                startLocation = j
                count+=1
            if ( count >= len(location)):
                break
        if ( count >= len(location)):
            break


    jouneylist.append(startLocation)#最後に終点を追加


    return jouneylist,jouneyTime


def InitDB():
    Spot.metadata.create_all(bind = ENGINE)
    SpotDist.metadata.create_all(bind = ENGINE)
    UserState.metadata.create_all(bind = ENGINE)


def sendFexMessage(event,place,time,pref):
    contents =[]

    for i in range(len(place)):
        print(place[i])
        boxc = BoxComponent(
            layout='baseline',
            spacing='sm',
            contents=[
                TextComponent( text='Place',color='#aaaaaa',size='sm',flex=2),
                TextComponent( text=place[i],wrap=True,color='#666666',size='sm',flex=8)
            ]
        )
        contents.append(boxc)

        if (i < len(place) - 1):
            box = BoxComponent(
                layout='baseline',
                spacing='sm',
                contents=[
                    TextComponent( 
                        text='↓\n↓   ' + str(int(time[i]/3600) ) +'h : ' + str(int(time[i]/60)%60 ) +'m \n↓',
                        color='#aaaaaa',size='sm',flex=1,wrap=True
                    ),
                ]
            )
            contents.append(box)




    headerImage = ImageComponent(# 画像ヘッダ
                    url='https://example.com/cafe.jpg',
                    size='full',
                    aspect_ratio='20:13',
                    aspect_mode='cover',
                )
    #--------------------------------------------------
    # コンテナ作成
    #--------------------------------------------------
    title = str(pref) +'旅行'
    bubble = BubbleContainer(
                direction='ltr',
                hero=headerImage,
                body=BoxComponent(
                    layout='vertical',
                    contents=[
                        # title
                        TextComponent(text= title , weight='bold', size='xl'),
                        # # info
                        BoxComponent(
                            layout='vertical',margin='lg',spacing='sm',contents=contents
                        )
                    ]
                )
            )

    message =[]
    message.append(FlexSendMessage(alt_text="旅程を作成したよ！", contents=bubble))
    message.append(TextSendMessage(text='これでどうかな？'))

    line_bot_api.reply_message(
        event.reply_token,
        message
    )



# -------------------------------------------
# メインルーチン
# -------------------------------------------
def mainRoutine(event=0,time=0,pref='大阪',StayTime =3600):
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
            spot.lat, spot.lng = getPointFromGoogleAPI(spot.name)
            db.session.commit()

    # # ----------------------------------------------------------
    # # BaseQueryオブジェクトから別のオブジェクトへ変更
    # # ----------------------------------------------------------
    location = []
    locationValue = {}
    for spot in spots:
        if (spot.lat != None):
            location.append(spot.name)
            locationValue[spot.name] = spot.score

    location = random.sample(location,5)

    # # ----------------------------------------------------------
    # #   i-jパスの設定
    # # ----------------------------------------------------------
    timeEdge ={}
    for i in spots:
        if (i.name not in location ):
            continue
        for j in spots:
            if (j.name not in location ):
                continue
            if (j.name == i.name):
                continue

            if (db.session.query(SpotDist).filter(SpotDist.id_from == i.id).filter(SpotDist.id_to == j.id).count() > 0 ):
                r = db.session.query(SpotDist).filter(SpotDist.id_from == i.id).filter(SpotDist.id_to == j.id)
                for r_elements in r:
                    timeEdge[i.name,j.name] = timeEdge[j.name,i.name] = r_elements.time
                    print("Data is discovered")
                continue

            if (db.session.query(SpotDist).filter(SpotDist.id_from == j.id).filter(SpotDist.id_to == i.id).count() > 0 ):
                r = db.session.query(SpotDist).filter(SpotDist.id_from == i.id).filter(SpotDist.id_to == j.id)
                for r_elements in r:
                    timeEdge[i.name,j.name] = timeEdge[j.name,i.name] = r.time
                    print("Data is discovered")
                continue


                
            # i-jパスがない時
            spotdist = SpotDist()
            spotdist.time = getPathromGoogleAPI([i.lat,i.lng],[j.lat,j.lng])
            spotdist.id_from,spotdist.id_to = i.id,j.id
            db.session.add(spotdist)
            db.session.commit()
            timeEdge[i.name,j.name] = timeEdge[j.name,i.name] = spotdist.time
            print("Call DirectionAPI : " + i.name +"-"+ j.name +"   time: " +str(spotdist.time) )

    # # ----------------------------------------------------------
    # #   i-jコストの設定
    # # ----------------------------------------------------------
    PointValue ={}
    for i in location:
        for j in location:
            PointValue[i, j] = PointValue[j, i] = locationValue[i] + locationValue[j]


    # # ----------------------------------------------------------
    # #   最適化問題の計算
    # # ----------------------------------------------------------
    route, point = calcPath(location, timeEdge, PointValue, time , StayTime)
    # # ----------------------------------------------------------
    # #   返送用メッセージを生成
    # # ----------------------------------------------------------
    # message = CreateResult(route, point)
    jouneySpot,moveTime = CreateResult(route, point,location,timeEdge)

    # # ----------------------------------------------------------
    # #   返送用Line構造体を生成
    # # ----------------------------------------------------------

    if (jouneySpot == None):
        line_bot_api.reply_message(event.reply_token,TextSendMessage(text='可能なプランがありません！'))
    else:
        sendFexMessage(event,jouneySpot,moveTime,pref = pref)


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
    m = re.match('.*(?<!\d)(\d\d?):(\d\d?)(?!\d).*[-|~|〜|ー|(から)].*(?<!\d)(\d\d?):(\d\d?)(?!\d).*', text)
    if m:
        starttime =  m.group(1).zfill(2)+":"+m.group(2).zfill(2)
        endtime   =  m.group(3).zfill(2)+":"+m.group(4).zfill(2)
        return starttime,endtime

    m = re.match('.*(?<!\d)(\d\d?)時.*[-|~|〜|ー|(から)].*(?<!\d)(\d\d?)時.*', text)
    if m:
        starttime =  m.group(1).zfill(2)+":00"
        endtime   =  m.group(2).zfill(2)+":00"
        return starttime,endtime

    return False

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


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    InitDB()
    text = event.message.text
    user_id = str(event.source.user_id)

    stateInstance = UserState()
    stateInstance.state='listen_word'
    print("------------GetTextMessage------------\n\n\n\n")
    print(text)
    # -------------------------------------------
    # ユーザーステート読込
    # -------------------------------------------  
    if (db.session.query(UserState).filter(UserState.user_id == user_id ).count() > 0 ):
        users = db.session.query(UserState).filter(UserState.user_id == user_id)
        for user in users:
            stateInstance = user
    print(stateInstance.state)


    # -------------------------------------------
    # テスト用
    # -------------------------------------------
    if (text in "テスト起動"):
        mainRoutine(event,22800,"大阪")
        return True

    # -------------------------------------------
    # 状態とテキストに応じて処理を記述
    # -------------------------------------------
    IsConversation = False
    if (stateInstance.state == 'listen_word'):
        if (getJourney(text)):
            print("◆getJourney")
            stateInstance.state = 'listen_pref_plan'
        else:# 意味のない会話
            IsConversation = True

    print(text)


    if (stateInstance.state == 'listen_pref_plan'):
        if (getPref(text) != False):
            print("◆getPref")
            stateInstance.pref = getPref(text)
            print(stateInstance.pref)
            stateInstance.state = 'listen_time_plan'

    print(text)


    if (stateInstance.state == 'listen_time_plan'):
        if (getTime(text) != False):
            print("◆getTime")
            stateInstance.StartTime,stateInstance.EndTime = getTime(text)
            dt1 = datetime.datetime.strptime(stateInstance.StartTime, '%H:%M')
            dt2 = datetime.datetime.strptime(stateInstance.EndTime, '%H:%M')
            MaxTravelingSeconds = (dt2 - dt1).total_seconds()
            mainRoutine(event,MaxTravelingSeconds,stateInstance.pref,stateInstance.StayTime)
            stateInstance.state = 'listen_word'


    if (getStop(text)):
        print("◆GetStop")
        stateInstance.state = 'stop'

    print(stateInstance.state)

    # -------------------------------------------
    # 状態に応じて返信メッセージを記述
    # -------------------------------------------
    if (stateInstance.state == 'listen_word'):
        if IsConversation:# 雑談フラグ作って、それが1なら返す
            line_bot_api.reply_message(event.reply_token,TextSendMessage(text='なにがしたい〜？旅行って言ってくれたら計画立てるよ'))
    elif (stateInstance.state =='listen_pref_plan'):
        line_bot_api.reply_message(event.reply_token,TextSendMessage(text='どの県にいきたい？'))
    elif (stateInstance.state =='listen_time_plan'):
        line_bot_api.reply_message(event.reply_token,TextSendMessage(text='何時から何時まで？\n 「hh:mmm-hh:mm」の形や「〇〇時から〇〇時まで」の形で入力してね'))
    elif (stateInstance.state == 'stop'):
        stateInstance.state = 'listen_word'
        line_bot_api.reply_message(event.reply_token,TextSendMessage(text='計画を中止したよ'))



    # -------------------------------------------
    # ユーザーステートを反映
    # -------------------------------------------     
    if (db.session.query(UserState).filter(UserState.user_id == user_id).count() > 0 ):
        print("updateState")
        users = db.session.query(UserState).filter(UserState.user_id == user_id)
        for user in users:
            user = stateInstance
    else:
        user = UserState()
        user = stateInstance
        user.user_id = user_id
        user.state = stateInstance.state
        db.session.add(user)
    db.session.commit()# コミット



    print(stateInstance.state)

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

#じゃらんからリストスクレイピングしてくる(未使用)
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
