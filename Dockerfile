FROM ubuntu:20.04

RUN mkdir /M5Server_app

RUN apt update -y && \
    apt install -y python3-pip python3-dev

RUN pip install --upgrade pip

ADD ./app/requirements.txt .

RUN pip install -r requirements.txt

COPY ./app/server /M5Server_app

EXPOSE 5000
EXPOSE 3125

CMD ["python3", "M5Server_app/app.py"]