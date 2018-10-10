# 旅のおとも
===============
行き先と時間を伝えると簡単に旅程を提案してくれるLINE BOT

## Description
旅のおともLINEで友達に追加した状態で行き先の県と滞在時間を伝えると対象の県からいくつか名所をピックアップし,滞在時間内でいい感じに周遊可能なプランを提示してくれるLINE BOTです.このBOTはLINE BOOTAWARDS向けに製作しました.

## Functions
- 

## Demo
YouTubeリンク or QRコード, URLを掲載予定です

## QR Code
![QR Code](./docs/qrcode.png "QR Code")

## Requirement
- Python 3.6
- Plugins
  - line-bot-sdk
  - Flask
  - PuLP
  - requests
  - gunicorn
  - Flask-SQLAlchemy
  - lxml
  - beautifulsoup4
  - psycopg2
- [SDK of the LINE Messagin API for Python](https://github.com/line/line-bot-sdk-python)
- Google Maps API
- Google Directions API


## Build & Setup
テストはngrokを用いた.
本番稼働はHerokuを用いると良い？
```
$ ngrok 5000
$ main.py 5000
```

## Future work
- 市,町単位の検索
- 移動手段に徒歩を追加
- スポットの羅列で提案
- `旅行プランの登録`と登録したプランを提案
  - 大阪旅行 by tomotan みたいな
  - 大阪旅行 by random みたいな
- ユーザーによる滞在時間の設定
- スポットと旅行プランの評価☆(1日一回とか)
- 現在地から対象の県までの計算
- リッチメニューの実装
  - おまかせ旅程
  - スポット登録
  - 旅記録登録(コメント)
  - 評価
  - 雑談


## Contribution
なにかあればIssuesまで

## Licence

[MIT](https://github.com/mikanbox/LineBot_Ryotei_Kun/blob/master/MIT-LICENSE.txt)

## Author

[mikanbox](https://github.com/mikanbox)
