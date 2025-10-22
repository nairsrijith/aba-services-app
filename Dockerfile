FROM python:3.13-slim

ENV LANG=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /myapp

RUN apt-get update && apt-get install -y build-essential libpq-dev gcc --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /myapp/requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . /myapp

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENV FLASK_APP=app
EXPOSE 8080

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]