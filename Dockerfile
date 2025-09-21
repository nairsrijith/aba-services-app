FROM python:3.13

WORKDIR /myapp

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["sh", "-c", "python init_db.py && python app.py"]