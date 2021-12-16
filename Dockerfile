# FROM latonaio/l4t-ds-opencv-7.2-jetpack-4.3:latest

# 大量に nvcr.io にリクエストを飛ばすと拒否されるので、
# Docker Hub の latona アカウントにイメージが publish してある場合はこれを使う
# FROM latonaio/deepstream-l4t:5.0-20.07-base

FROM nvcr.io/nvidia/deepstream-l4t:5.0-20.07-base

# Definition of a Device & Service
ENV POSITION=Runtime \
    SERVICE=template-matching-by-opencv-for-rtsp \
    AION_HOME=/var/lib/aion

RUN mkdir ${AION_HOME}
WORKDIR ${AION_HOME}

RUN apt-get update && apt-get install -y \
    libglib2.0 \
    libgl1 \
    libgstrtspserver-1.0-dev \
    libgirepository1.0-dev \
    libcairo2-dev \
    gstreamer1.0-rtsp \
    build-essential \
    software-properties-common \
    curl

# python3-gi モジュールに依存しているので、先に使ってしまう
# (software-properties-common パッケージによりインストールされたコマンド)
#
# Python の様々なバージョンのバイナリパッケージがあるリポジトリを追加する
RUN add-apt-repository ppa:deadsnakes/ppa

# 手動で追加する PyGObject (import gi の提供元パッケージ) と競合するので削除する
RUN apt-get remove -y python3-gi

# 追加したバイナリパッケージから Python 3.9 をインストールする
RUN apt-get install -y \
    python3.9-dev \
    python3.9-distutils

RUN apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# pip がインストールされていないので、手動インストール
RUN curl https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py \
    && python3.9 /tmp/get-pip.py \
    && rm -rf /tmp/get-pip.py

# Setup Directoties
RUN mkdir -p \
    $POSITION/$SERVICE
WORKDIR ${AION_HOME}/$POSITION/$SERVICE/
ADD . .

RUN pip3.9 install -r requirements.txt
RUN python3.9 setup.py install

CMD ["/bin/sh", "docker-entrypoint.sh"]