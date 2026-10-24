FROM python:3.12-slim
WORKDIR /srv
COPY server/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY server/app ./app
COPY web /srv/web
ENV FLOWDESK_DB=/data/flowdesk.db
VOLUME ["/data"]
EXPOSE 8000
CMD ["sh", "-c", "python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
