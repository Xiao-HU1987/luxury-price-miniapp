FROM python:3.11-slim

WORKDIR /app

COPY server/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY server/ ./

ENV PORT=8080
ENV DEBUG=False
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["bash", "start.sh"]
