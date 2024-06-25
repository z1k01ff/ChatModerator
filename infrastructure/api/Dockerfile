FROM python:3.11-slim

WORKDIR /usr/src/app/api

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . /usr/src/app/api