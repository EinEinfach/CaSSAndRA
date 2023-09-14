	FROM python:3.10-slim
    WORKDIR /usr/src/cassandra
    COPY ./requirements.txt /usr/src/cassandra
	RUN pip install --upgrade pip
	RUN pip install -r requirements.txt
	COPY ./CaSSAndRA .
	CMD ["python3","app.py"]