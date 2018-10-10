import re

tt_ksuji = str.maketrans('一二三四五六七八九〇壱弐参', '1234567890123')




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
        pattern = r".*(" + p + r").*"
        match = re.search(pattern, text)
        if match:
            return match.group(1) #テキスト(県名)を返す
    return False

# 何時から何時まで？
def getTime(text):
    tex = text.translate(tt_ksuji)
    m = re.match('.*(?<!\d)(\d\d?):(\d\d?)(?!\d).*[-|~|〜|ー|(から)].*(?<!\d)(\d\d?):(\d\d?)(?!\d).*', tex)
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

# 何時間くらい?
def getSumTime(text):
    tex = text.translate(tt_ksuji)
    m = re.match('.*(?<!\d)(\d\d?)(?!\d)時間.*', tex)
    if m:
        starttime =  "00:00"
        endtime   =  m.group(1).zfill(2)+":00"
        return starttime,endtime

    m = re.match('.*(?<!\d)(\d\d?):(\d\d?)(?!\d).*', text)
    if m:
        starttime =  "00:00"
        endtime   =  m.group(1).zfill(2)+":"+m.group(2).zfill(2)
        return starttime,endtime
    return False



def getStop(text):
    for p in ['やめる','やめた','終了','止める','止めた']:
        pattern = r".*" + p + r".*"
        match = re.search(pattern, text)
        if match:
            return True #テキスト(県名)を返す
    return False

def getHelp(text):
    for p in ['HELP','ヘルプ','へるぷ','Help','help']:
        pattern = r".*" + p + r".*"
        match = re.search(pattern, text)
        if match:
            return True #テキスト(県名)を返す
    return False

def getSpot(text):
    for p in ['登録','とうろく']:
        pattern = r".*" + p + r".*"
        match = re.search(pattern, text)
        if match:
            return True #テキスト(県名)を返す
    return False


