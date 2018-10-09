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

# リストをスクレイピング(未使用)
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