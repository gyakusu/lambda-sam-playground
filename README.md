# lambda-sam-playground

AWS Lambda と AWS SAM を MacBook 上で学ぶための playground です。

## 学習の流れ

最初は AWS へデプロイせず、次の流れを体験します。

MacBook → Docker → AWS SAM CLI → ローカル Lambda

その後、Lambda 用コンテナイメージや AWS へのデプロイへ進みます。

## 現在の構成

```text
lambda-sam-playground/
├── data/
│   └── sample.csv
├── events/
│   ├── event.json
│   └── statistics-event.json
├── src/
│   ├── hello_world/
│   │   └── app.py
│   └── statistics/
│       ├── app.py
│       └── requirements.txt
├── template.yaml
├── .gitignore
└── README.md
```

## Lambda 関数

### `HelloWorldFunction`

`GET /hello` に対応する最小の Lambda です。

### `StatisticsFunction`

`POST /statistics` に CSV を送ると、CSV 内の数値列ごとに次を計算します。

- 件数
- 平均
- 中央値
- 標準偏差
- 最大値
- 最小値

`pandas` で CSV を読み込み、`numpy` で統計量を計算します。

標準偏差は `numpy.std(..., ddof=0)` を使っているため、母標準偏差です。標本標準偏差にしたい場合は `ddof=1` に変更できます。

## なぜ `requirements.txt` が必要なのか

Lambda の Python ランタイムには、アプリケーションが追加した `numpy` や `pandas` は自動では含まれません。

`requirements.txt` に依存パッケージを書き、`sam build` で Lambda のビルド成果物へ含めます。

NumPy / pandas にはネイティブコードが含まれるため、Mac 上でそのまま依存関係を構築して Linux の Lambda コンテナへ持ち込むのではなく、今回は `sam build --use-container` を使います。

## ビルド

```bash
sam validate
sam build --use-container
```

`--use-container` によって SAM は Lambda に近い Linux コンテナ内で依存関係をビルドします。

## Hello World を直接 invoke

```bash
sam local invoke HelloWorldFunction --event events/event.json
```

## Statistics Lambda を直接 invoke

```bash
sam local invoke StatisticsFunction --event events/statistics-event.json
```

## HTTP API を起動

```bash
sam local start-api
```

別ターミナルから Hello World:

```bash
curl http://127.0.0.1:3000/hello
```

CSV ファイルを送る:

```bash
curl \
  -X POST \
  -H 'Content-Type: text/csv' \
  --data-binary @data/sample.csv \
  http://127.0.0.1:3000/statistics
```

## Docker と Lambda の関係

`sam local invoke` / `sam local start-api` では、AWS SAM CLI が Docker コンテナを使って Lambda に近い実行環境を作ります。

今回の構成では概念的に次の役割分担です。

- MacBook: 開発場所
- Docker: コンテナを起動する仕組み
- SAM CLI: Lambda 用のローカル実行環境を組み立てるツール
- `app.py`: Lambda が実行する処理
- `requirements.txt`: Lambda に含める Python 依存関係

## CSV を「大量」にする場合の注意

今回の `/statistics` は CSV を HTTP リクエスト本文として Lambda に渡す学習用の構成です。

実際の AWS Lambda では、同期 invocation のリクエストとレスポンスはそれぞれ 6 MB が上限です。そのため、本当に大きな CSV を処理するときは、HTTP で丸ごと Lambda に送るより、S3 に CSV を置いて Lambda が S3 から読む構成へ発展させるのが自然です。

次の学習では、`sam local start-api` から S3 イベントへ発展させます。

## 次の実験

1. `sam local start-api` で HTTP → Lambda → pandas → NumPy を確認
2. `sam build --use-container` が何を作っているか確認
3. Lambda 用 `Dockerfile` を自作して `PackageType: Image` を試す
4. NumPy / pandas より大きい依存関係として PyTorch を検討する
5. 最後に AWS Lambda へデプロイする
