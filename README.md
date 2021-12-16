# template-matching-by-opencv-for-rtsp
template-matching-by-opencv-for-rtspは、rtspで配信されているカメラ映像に対してOpenCVでテンプレートマッチングを行うマイクロサービスです。  
本サービスでは予め指定したテンプレート画像、及び閾値を元にテンプレートマッチングを行います。  
なお、テンプレート画像はRabbitMQを介して取得されます。  

## 動作環境
AIONのプラットフォーム上での動作を前提としております。使用する際は、事前にAIONの動作環境を用意してください。
本サービスを使用するためには映像がRTSPで配信されている必要があります。

* Linux OS
* ARM/AMD/Intel
* Kubernetes
* AION 
* RTSPサーバ(カメラ映像配信)

## Installation

```
cd ~/$(hostname)/Runtime
git clone git@bitbucket.org:latonaio/template-matching-by-opencv-for-rtsp.git -b feature/kubernetes

# template-matching-by-opencv-for-rtspが参照する用のデータディレクトリを作成する。
sudo mkdir -p /var/lib/aion/prj/Data/template-matching-by-opencv-for-rtsp/

# Dockerイメージをビルドする.
make docker-build

# デフォルトで読み込む画像ファイルを配置する。
sudo cp ~/$(hostname)/Runtime/template-matching-by-opencv-for-rtsp/file/data/dummy.jpg /var/lib/aion/prj/Data/template-matching-by-opencv-for-rtsp/
```

### デプロイ on AION
AION上でデプロイする場合、services.yamlに次の設定を追加してください。
```
 template-matching-by-opencv-for-rtsp-1:
    scale: 1
    startup: yes
    always: yes
    network: NodePort
    env:
      PROCESS_NUM: 1
      CAMERA_SERVICE: stream-usb-video-by-rtsp-multiple-camera
      MATCHING_RESULT_MODE: LATEST
      RABBITMQ_URL: amqp://guest:guest@rabbitmq:5672/pokayoke
      QUEUE_ORIGIN: template-matching-by-opencv-for-rtsp-1-queue
    ports:
      - name: fitness
        protocol: TCP
        port: 5000
        nodePort: 32001
        
```
## Docker Build
使用するカメラが一台の場合は、本レポジトリの docker-build.sh を用いてDockerコンテナをビルドしてください。  
使用するカメラが複数の場合は、複数のDockerコンテナをビルドする必要があります。  
複数の場合は、本レポジトリの docker-build-multi.sh を用いてDockerコンテナをビルドしてください。  


## I/O  
### input
以下のデータがRabbitMQによりインプットされます。  

* テンプレート画像の情報
* rtspプロトコルで配信されている映像

入力データ例:  
```
INIT_TEMPLATE_DATA = [
    {
        "template_image": {
            "path": INIT_IMAGE_PATH,
            "trim_points": [[0, 0], [355, 254]],
        },
        "image": {
            "trim_points": [[0, 0], [355, 254]],
            "trim_points_ratio": 0.02,
        },
        "metadata": {
            "template_id": 1,
            "work_id": 1,
            "pass_threshold": 0.8,
        }
    },
]
```
### output        
RabbitMQへメタデータ(類似度、類似箇所、合格判定)を出力します。   
RabbitMQへの出力データ例:
```
metadata = {
  "fitness": [
    {
      "matching_rate": 9.6553,
      "matching_points": {
        "x": 145,
        "y": 340,
        "w": 46,
        "h", 100,
      },
      "is_pass": True
    }
  ] 
}
```

## Architecture
System Architecture
![](file/for-readme/template-matching-by-opencv-for-rtsp_ファイル構成.jpg "SystemArchitecture")
TemplateMatching Architecture
![](file/for-readme/matching_architecture.jpg "TemplateMatchingArchitecture")

src/templatematching/
* core.py  
上記I/Oに書かれているとおりに処理を実行します。実行には各種外部ライブラリ及び下記の内部ライブラリを使用します。  

* gst.py  
ストリーミングカメラから画像を取得するためのパイプライン構築及び画像の取得を可能にします。  

* streaming_match.py  
テンプレート画像と入力画像のマッチングプロセスを構築するためのクラスが記述されています。  

* rtsp_server.py  
rtspサーバーの構築及び接続を可能にするためのクラスが記述されています。  

* result_redis.py  
結果をマッチング率などの情報をRedisサーバーに書き込むためのクラスが記述されています。  

src/templatematching/template_matching/
* cv2_image.py  
画像の読み込み、切り抜き、モノクロ処理などOpenCVの機能を使用したテンプレートマッチングに必要な画像処理を可能にする関数が記述されています。  

* cv2_template_matching.py  
テンプレートマッチングの精度や方法、また実行するための関数が記述されています。  

* matcher.py  
テンプレート画像の設定や、上記二つのファイルに記述されている関数を用いて実際にテンプレートマッチングを行い結果を出力するための処理が記述されています。  
