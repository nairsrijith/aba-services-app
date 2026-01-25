FROM python:3.13

ENV PYTHONUNBUFFERED=1

WORKDIR /myapp

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev pkg-config postgresql-client \
    libglib2.0-0 libcairo2 libcairo2-dev gir1.2-gtk-3.0 \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Make python3 the default python
RUN ln -s /usr/bin/python3 /usr/bin/python

# install python deps
COPY requirements.txt requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# copy project
COPY . /myapp

# make send_reminders.py executable
RUN chmod +x /myapp/send_reminders.py

# entrypoint script
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# use flask factory for CLI/migrations
ENV FLASK_APP=app:create_app
EXPOSE 8080

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]