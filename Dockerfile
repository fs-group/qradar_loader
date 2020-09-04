FROM python:3.8
RUN apt update

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

ADD requirements.txt /usr/src/app/

RUN pip3 install --no-cache-dir -r requirements.txt
ADD . /usr/src/app
