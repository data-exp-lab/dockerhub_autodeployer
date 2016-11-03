FROM ubuntu:16.04
RUN apt-get update && apt-get install -qy software-properties-common python-software-properties && \
  apt-get update && apt-get install -qy \
    build-essential \
    git \
    wget \
    libffi-dev \
    libpython-dev && \
  apt-get clean && rm -rf /var/lib/apt/lists/*

RUN wget https://bootstrap.pypa.io/get-pip.py && python get-pip.py
RUN pip install docker-py requests tornado

WORKDIR /srv
COPY ./serve.py /srv/serve.py
EXPOSE 80
CMD ["python", "serve.py"]
