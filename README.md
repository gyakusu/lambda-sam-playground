# lambda-sam-playground

AWS Lambda と AWS SAM を MacBook 環境で学ぶための学習用プロジェクト（Playground）です。

## 学習の流れ

最初は AWS へ直接デプロイせず、ローカル環境で以下のフローを体験します。

MacBook → Docker → AWS SAM CLI → ローカル Lambda

その後、Lambda 用コンテナイメージの作成や、実際の AWS 環境へのデプロイへとステップアップします。

## 必須ツールとバージョン

以下はこの手順の動作確認に使用したバージョンです（2026-09-26）。SAM テンプレートの Python ランタイムは `python3.13` です。

| ツール | バージョン・必要条件 |
| --- | --- |
| macOS | AWS SAM CLI のサポート対象である macOS 13 以降 |
| Python | 3.13（Lambda ランタイム。`uv` が管理できます） |
| Docker Desktop | 最新安定版を推奨（確認環境の Docker Engine は 29.8.0）。Linux コンテナを実行でき、Docker Engine が起動中であること。メモリは 8 GB 以上を推奨 |
| AWS SAM CLI | 1.166.2 で確認 |
| `uv` | 0.12.19 で確認 |
| LocalStack CLI (`lstk`) | 1.2.0 で確認 |

バージョン確認には `sam --version`、`uv --version`、`lstk --version`、`docker version` を使用します。表のバージョンは動作確認時の基準で、各ツールは新しい安定版を推奨します。`lstk` が起動する LocalStack イメージのバージョンは CLI とは別で、`lstk start` が管理します。このプロジェクトではイメージのタグを固定していません。

[Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/) をインストールし、起動して Linux コンテナを利用できる状態にします。`sam build --use-container`、`sam local`、LocalStack は Docker Engine を使用するため、Docker Desktop が停止していると実行できません。

### AWS SAM CLI のインストール

[AWS SAM CLI の公式インストール手順](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)から macOS 用インストーラーを入手します。Apple Silicon は ARM64、Intel Mac は x86_64 を選びます。

* [Apple Silicon 用インストーラー](https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-macos-arm64.pkg)
* [Intel Mac 用インストーラー](https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-macos-x86_64.pkg)

### `uv` のインストール

Homebrew を使う場合:

```bash
brew install uv
uv --version
```

Homebrew を使わない場合は、[uv 公式インストール手順](https://docs.astral.sh/uv/getting-started/installation/)を参照してください。

### LocalStack CLI のインストール

```bash
brew install localstack/tap/lstk
lstk --version
```

LocalStack の AWS サービスを利用する際は、初回起動時にブラウザーでの認証が必要です。詳細は[LocalStack CLI の公式手順](https://docs.localstack.cloud/aws/developer-tools/running-localstack/lstk/)を参照してください。

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

既存バケットを SAM で新規作成しないよう、バケット名は `StatisticsBucketName` パラメーターで指定します（デフォルトは `lambda-sam-playground-data`）。S3 から EventBridge への通知を有効にする必要があります。LocalStackで試す手順は、下の「S3StatisticsFunctionをLocalStackで動作確認」を参照してください。実AWSでは対象バケットの **Properties → Event notifications → Amazon EventBridge** を有効にしてからアップロードします。EventBridgeを有効にする前にアップロード済みのオブジェクトは、このイベントの対象になりません。

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

初回起動前、および関数コードや依存関係を変更した後は、プロジェクトのルートでビルドします。特に pandas と NumPy は Linux コンテナ向けにビルドする必要があります。

```bash
sam build --use-container
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

`data/sample.csv` を送信すると、HTTP レスポンスは次の JSON になります。

```json
{
  "columns": {
    "value": {
      "count": 5,
      "mean": 30.0,
      "median": 30.0,
      "std": 14.142135623730951,
      "max": 50.0,
      "min": 10.0
    },
    "score": {
      "count": 5,
      "mean": 300.0,
      "median": 300.0,
      "std": 141.4213562373095,
      "max": 500.0,
      "min": 100.0
    }
  }
}
```

`GET /hello` のレスポンス例:

```json
{"message":"Hello from local Lambda!"}
```

## S3StatisticsFunctionをLocalStackで動作確認

Dockerが起動していることを確認してから、次の手順でLocalStack上にSAMアプリをデプロイし、S3アップロードからLambdaログまでを確認します。`lstk sam deploy`はSAMを使ってLocalStackへデプロイします。実AWSにはデプロイしません。

### 1. LocalStack を起動

```bash
lstk start
lstk status

```

### 2. SAMアプリをビルドしてデプロイ

```bash
lstk sam build --use-container
lstk sam deploy \
  --stack-name lambda-sam-playground \
  --resolve-s3 \
  --capabilities CAPABILITY_IAM \
  --no-confirm-changeset \
  --no-progressbar \
  --region us-east-1 \
  --parameter-overrides StatisticsBucketName=lambda-sam-playground-data

```

### 3. 対象S3バケットのEventBridge通知を有効化

```bash
lstk aws s3api put-bucket-notification-configuration \
  --bucket lambda-sam-playground-data \
  --notification-configuration '{"EventBridgeConfiguration":{}}'

```

このコマンドはバケットの通知設定全体を置き換えます。専用の学習用バケットであることを確認してから実行してください。EventBridgeを有効にする前にアップロードしたオブジェクトはトリガーされません。

### 4. CSVをアップロード

```bash
lstk aws s3 cp data/sample.csv \
  s3://lambda-sam-playground-data/verification/statistics-smoke.csv

```

### 5. Lambdaのログを確認

CloudFormationから関数名を取得し、その関数のログを表示します。

```bash
FUNCTION_NAME=$(lstk aws cloudformation describe-stack-resource \
  --stack-name lambda-sam-playground \
  --logical-resource-id S3StatisticsFunction \
  --query 'StackResourceDetail.PhysicalResourceId' \
  --output text)
lstk aws logs tail "/aws/lambda/${FUNCTION_NAME}" --since 15m --format short

```

ログに`S3 CSV statistics`と列ごとの件数・平均・中央値・標準偏差・最大値・最小値が出ていれば成功です。新しいログを継続して確認する場合は、末尾に`--follow`を追加します。

LocalStack全体を停止する場合は`lstk stop`を実行します。これはSAMスタックのリソース削除とは別です。デプロイしたスタックも削除する場合は、次を実行します。

```bash
lstk aws cloudformation delete-stack --stack-name lambda-sam-playground

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

S3 イベントによる実行は、上記の手順でLocalStack上でも確認できます。

## 次の学習ステップ

1. `sam local start-api` で、HTTP リクエスト → Lambda → pandas → NumPy の一連の処理フローを確認する
2. `sam build --use-container` によって生成されるビルド成果物の中身を確認する
3. Lambda 用の `Dockerfile` を自作して、コンテナイメージ形式 (`PackageType: Image`) でのデプロイを試す
4. NumPy や pandas よりファイルサイズの大きいライブラリ（PyTorch など）の導入を検証する
5. 最終的に実際の AWS 環境（AWS Lambda）へデプロイする
