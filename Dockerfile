FROM python:3.13

WORKDIR /myapp

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY . .

EXPOSE 8080

ENTRYPOINT [ "python", "init_db.py" ]

CMD ["python", "app.py"]
