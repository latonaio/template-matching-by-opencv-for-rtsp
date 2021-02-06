# FROM latonaio/l4t-ds-opencv-7.2-jetpack-4.3:latest
FROM latonaio/l4t-ds-opencv-7.2-jetpack-4.4:latest

# Definition of a Device & Service
ENV POSITION=Runtime \
    SERVICE=template-matching-by-opencv-for-rtsp \
    AION_HOME=/var/lib/aion

RUN mkdir ${AION_HOME}
WORKDIR ${AION_HOME}

RUN apt-get update && apt-get install -y \
    libgstrtspserver-1.0-dev \
    gstreamer1.0-rtsp \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Setup Directoties
RUN mkdir -p \
    $POSITION/$SERVICE
WORKDIR ${AION_HOME}/$POSITION/$SERVICE/
ADD . .

RUN pip3 install redis
RUN python3 setup.py install

CMD ["/bin/sh", "docker-entrypoint.sh"]
