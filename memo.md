# デプロイメモ
## LINE BOTメモ
- [参考資料](https://qiita.com/n0bisuke/items/ceaa09ef8898bee8369d)

URL
- [LINE developers](https://at.line.me/jp/)

- LINE DevのWebhookに設定するURL
  - [heroku](https://linebot-ryotei-kun.herokuapp.com:443/callback)
  - [hgrok](ターミナルに出てくるやつ)



### herokuについて
- dynoは30分以上トラフィックがないとsleepする

### log1
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
- heroku config:set LineMessageAPIChannelAccessToken=" key " --app linebot-ryotei-kun
- heroku config:set LineMessageAPIChannelSecret=" key " --app linebot-ryotei-kun
- requirements.txtにgnuicornを追加したらビルド通った
- demo.pyが成功

### log2
- Procfileをmain.pyに
- syntax errorが出てる
- pulpの定式化を修正
- main.pyの動作を確認



### log3
- DBの導入
  - https://qiita.com/croquette0212/items/9b4dc5377e7d6f292671
  - Sqlアルケミーを利用してDBをオブジェクト管理

- 観光地リストの自動取得
  - google検索 おすすめスポット api
  - API利用:[公共クラウドシステム](https://www.chiikinogennki.soumu.go.jp/k-cloud-api/genre/137.html)
  - 権利関係はちゃんと確認したほうがいい

- ノード一つしかなかった場合の出力訂正
- なんか1回じゃデータ送れていない時がある
  - データ送信のステップがおかしいのでちゃんと表示したほうがいいかも.....


- 応答を修正
- herokuには30秒のタイムアウトがある
- 既存バグを全て修正
- 正規表現追加
- 内包表現の追加
- ステートマシン追加? いらんくね？

- 状態遷移の修正
- ※定式化に修正が必要
- flexSample実装
 

### ngrokについて
- ローカル環境をトンネリングしてグローバルIPを割り当て

## 履歴
- Heroku初デプロイ
- heroku log に　error message "No web processes running"


