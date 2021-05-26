from python:3.9

RUN apt update
RUN apt install sqlite3

WORKDIR /app
COPY . /app

RUN pip install -r requirements.txt

ENV FLASK_APP app.py
ENV FLASK_ENV development

EXPOSE 5000

# CMD ["flask", "run", "--host=0.0.0.0"]
CMD ["python3", "app.py"]
