# lambda-sam-playground

AWS Lambda と AWS SAM を MacBook 環境で学ぶための学習用プロジェクト（Playground）です。

## 学習の流れ

最初は AWS へ直接デプロイせず、ローカル環境で以下のフローを体験します。

MacBook → Docker → AWS SAM CLI → ローカル Lambda

その後、Lambda 用コンテナイメージの作成や、実際の AWS 環境へのデプロイへとステップアップします。

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
│       ├── pyproject.toml
│       ├── requirements.txt
│       └── uv.lock
├── template.yaml
├── .gitignore
└── README.md

```

## Lambda 関数

### `HelloWorldFunction`

`GET /hello` に対応する最小構成の Lambda 関数です。

### `StatisticsFunction`

`POST /statistics` に CSV データを送信すると、CSV 内の数値列ごとに以下の統計量を計算します。

* 件数
* 平均
* 中央値
* 標準偏差
* 最大値
* 最小値

`pandas` で CSV を読み込み、`numpy` で計算を行っています。

### `S3StatisticsFunction`

既存の S3 バケット `lambda-sam-playground-data` に CSV オブジェクトがアップロードされると、`StatisticsFunction` と同じ統計量を計算します。結果は Lambda の CloudWatch Logs に JSON で出力されます。

既存バケットを SAM で新規作成しないよう、バケット名は `StatisticsBucketName` パラメーターで指定します（デフォルトは `lambda-sam-playground-data`）。S3 から EventBridge への通知を有効にする必要があります。AWS コンソールで対象バケットの **Properties → Event notifications → Amazon EventBridge** を有効にしてからアップロードしてください。EventBridge を有効にする前にアップロード済みのオブジェクトは、このイベントの対象になりません。

対象バケットで CSV をアップロードすると処理が起動します。CSV 以外の拡張子は処理しません。

## Python 依存関係の管理

Lambda の標準の Python ランタイムには、`numpy` や `pandas` といった外部ライブラリは含まれていません。

本プロジェクトでは `src/statistics/` を `uv` プロジェクトとして設定し、依存関係を `pyproject.toml` と `uv.lock` で一元管理しています。
AWS SAM はビルド時に `requirements.txt` を参照するため、`uv export` コマンドを使用してこれを出力します。

依存関係を追加・更新する場合は、以下のように実行します。

```bash
cd src/statistics
uv add scipy
uv export --format requirements.txt --output-file requirements.txt --no-dev
cd ../..

```

依存関係をローカルの開発環境に同期させる場合は、以下のコマンドを使用します。

```bash
cd src/statistics
uv sync --locked --no-dev

```

生成された `requirements.txt` は、`sam build` 実行時に Lambda のビルドアーティファクト（成果物）に含められます。

NumPy や pandas にはネイティブコード（C拡張など）が含まれるため、Mac 上でビルドしたものをそのまま Linux ベースの Lambda コンテナに持ち込んでも動作しません。そのため、今回は `sam build --use-container` を使用してビルドを行います。

## ビルド

```bash
sam validate
sam build --use-container

```

`--use-container` オプションを指定することで、SAM は実際の Lambda に近い Linux コンテナ内で依存関係のビルドを行います。

## HelloWorldFunction のローカル実行 (invoke)

```bash
sam local invoke HelloWorldFunction --event events/event.json

```

## StatisticsFunction のローカル実行 (invoke)

```bash
sam local invoke StatisticsFunction --event events/statistics-event.json

```

## HTTP API のローカル起動

```bash
sam local start-api

```

別のターミナルを開き、以下のコマンドで Hello World を確認します:

```bash
curl http://127.0.0.1:3000/hello

```

CSV ファイルを送信して統計処理を実行する場合:

```bash
curl \
  -X POST \
  -H 'Content-Type: text/csv' \
  --data-binary @data/sample.csv \
  http://127.0.0.1:3000/statistics

```

## Docker と Lambda の関係

`sam local invoke` や `sam local start-api` を実行すると、AWS SAM CLI は Docker コンテナを使用して実際の Lambda に近い実行環境をシミュレートします。

本構成における概念的な役割分担は以下の通りです。

* MacBook: 開発環境（ホストOS）
* Docker: コンテナの実行環境
* AWS SAM CLI: Lambda のローカル実行環境を構築・管理するツール
* `app.py`: Lambda 関数として実行されるメイン処理
* `requirements.txt`: Lambda 環境にインストールする Python パッケージのリスト

## 大容量の CSV を扱う場合の注意点

今回の `/statistics` エンドポイントは、学習用に CSV を HTTP リクエストボディに含めて Lambda に渡す構成にしています。

しかし、実際の AWS Lambda では、同期呼び出し (Synchronous invocation) のペイロードサイズはリクエスト・レスポンスともに最大 6 MB に制限されています。そのため、実際のプロダクションで大きな CSV を処理する場合は、HTTP リクエストで直接送信するのではなく、「ファイルを Amazon S3 にアップロードし、Lambda がそれを読み込む」アーキテクチャにするのが一般的です。

今後の学習ステップでは、`sam local start-api`（API Gateway のシミュレーション）から、S3 イベントをトリガーとした実行へとステップアップしていく予定です。

## 次の学習ステップ

1. `sam local start-api` で、HTTP リクエスト → Lambda → pandas → NumPy の一連の処理フローを確認する
2. `sam build --use-container` によって生成されるビルド成果物の中身を確認する
3. Lambda 用の `Dockerfile` を自作して、コンテナイメージ形式 (`PackageType: Image`) でのデプロイを試す
4. NumPy や pandas よりファイルサイズの大きいライブラリ（PyTorch など）の導入を検証する
5. 最終的に実際の AWS 環境（AWS Lambda）へデプロイする
