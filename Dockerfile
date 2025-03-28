FROM python:3.10

WORKDIR /app


COPY ./requirements.txt /code/requirements.txt


RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt


COPY . ..

ENV PYTHONPATH="${PYTHONPATH}:/app:/tests"

#CMD ["fastapi", "run", "/app/app.py", "--reload", "--proxy-headers", "--port", "80"]