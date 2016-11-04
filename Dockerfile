FROM python:3.5-alpine
RUN pip install docker-py requests tornado

WORKDIR /srv
COPY ./serve.py /srv/serve.py
EXPOSE 80
CMD ["python3", "-m", "serve"]
