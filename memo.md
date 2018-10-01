# デプロイメモ
## LINE BOTメモ
- [参考資料](https://qiita.com/n0bisuke/items/ceaa09ef8898bee8369d)

URL
- [LINE developers](https://at.line.me/jp/)

- LINE DevのWebhookに設定するURL
  - [heroku](https://linebot-ryotei-kun.herokuapp.com:443/callback)
  - [hgrok](ターミナルに出てくるやつ)



### herokuについて
- [参考資料](https://b-side.work/2017/02/heroku-and-git/)
- [参考資料2](https://qiita.com/hirosat/items/39cd6ba954a451bc01b8)
- [参考資料3](https://qiita.com/sqrtxx/items/2ae41d5685e07c16eda5)
- リモートリポジトリのmasterにgit pushすることで、デプロイを実行
- heroku logs –a linebot-ryotei-kun --tail サーバー側を監視(-aでエラー)
- heroku logs --tail サーバー側を関し
- pip freezeを使って依存ライブラリをrequirements.txtに書き出し
- Procfileに起動Commandを記入
- git push heorku master
  - エラーが503(内部エラー)に変わった
- herokuの環境変数にトークン追加
- heroku config:set LineMessageAPIChannelAccessToken={iGl4or4uXfRGwd9w0dk8UoDMDWn4z7KGtjSMC67WkwzJERiD+FLHwIkEhLeRCXLwuSg4MVuIvoVCDoxPjsJ9azXNe5MTPhPTWwBpf8e+1uuSW/FCL38Naqb0hehsaIqdoDApewB07WrdMuIR0bWMvQdB04t89/1O/w1cDnyilFU=} --app linebot-ryotei-kun

heroku config:set LineMessageAPIChannelSecret={c9f4a586a8d8b03ce5f6008e79d1414e} --app linebot-ryotei-kun



### ngrokについて
- ローカル環境をトンネリングしてグローバルIPを割り当て


## 履歴
- Heroku初デプロイ
- heroku log に　error message "No web processes running"


