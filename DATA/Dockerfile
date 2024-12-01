FROM python:3.9

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

COPY . .

CMD ["sh", "-c", "python3 ./influxAdaptor.py & streamlit run WebService.py --server.address=0.0.0.0 & streamlit run parking_stats.py --server.address=0.0.0.0"]

