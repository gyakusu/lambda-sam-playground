# lambda-sam-playground

AWS Lambda と AWS SAM を MacBook 上で学ぶための最小構成の playground です。

## このプロジェクトで理解すること

最初は AWS へデプロイせず、次の流れだけを体験します。

MacBook → Docker → AWS SAM CLI → ローカル Lambda

その後、次の実験へ進みます。

- `sam build` によるビルド
- `sam local invoke` による直接 invoke
- `sam local start-api` による HTTP 経由の invoke
- Docker 上で動いている Lambda ランタイムの確認
- Lambda 用コンテナイメージ (`PackageType: Image`) の作成
- AWS Lambda へのデプロイ
- NumPy / PyTorch など大きな依存関係を持つ Lambda の構築

## 最小構成

```text
lambda-sam-playground/
├── events/
│   └── event.json
├── src/
│   └── hello_world/
│       └── app.py
├── template.yaml
├── .gitignore
└── README.md
```

`sam build` を実行すると `.aws-sam/` が生成されます。これは生成物なので Git には含めません。

## ファイルの役割

### `template.yaml`

AWS SAM の設計図です。

`AWS::Serverless::Function` によって Lambda 関数を定義し、`CodeUri`、`Handler`、`Runtime`、API イベントなどを指定します。

AWS SAM CLI はこのテンプレートをもとにローカル実行や、将来の AWS へのデプロイに必要な情報を組み立てます。

### `src/hello_world/app.py`

Lambda が呼び出されたときに実行される Python コードです。

`app.lambda_handler` は「`app.py` の `lambda_handler` 関数」という意味です。

### `events/event.json`

`sam local invoke` の入力イベントです。

今回はイベントを使わない極小関数なので `{}` だけにしています。

## ローカル実行

### 1. SAM テンプレートの検証

```bash
sam validate
```

### 2. ビルド

```bash
sam build
```

`.aws-sam/` にビルド成果物が作られます。

### 3. 直接 invoke

```bash
sam local invoke HelloWorldFunction --event events/event.json
```

### 4. HTTP API として起動

```bash
sam local start-api
```

別ターミナルから:

```bash
curl http://127.0.0.1:3000/hello
```

## Docker と Lambda の関係

`sam local invoke` / `sam local start-api` では、AWS SAM CLI が Docker コンテナを使って Lambda の実行環境に近い環境を作ります。

つまり、今回の構成では概念的に次の役割分担です。

- MacBook: 開発場所
- Docker: コンテナを起動する仕組み
- SAM CLI: Lambda 用コンテナを準備して、関数を Lambda らしい形で呼び出すツール
- `app.py`: Lambda の実際の処理

重要なのは、SAM CLI が Lambda そのものではないことです。SAM は Lambda などのサーバーレスリソースを定義・構築・ローカルテスト・デプロイしやすくするためのフレームワーク / CLI です。

## 次の実験

次の段階では通常の ZIP ベースの Lambda と、Dockerfile から作る `PackageType: Image` の Lambda を比較します。
