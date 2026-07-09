FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN addgroup --system terrapoint && adduser --system --ingroup terrapoint terrapoint
COPY --chown=terrapoint:terrapoint . .
USER terrapoint
EXPOSE 8099
CMD ["uvicorn", "api.index:app", "--host", "0.0.0.0", "--port", "8099"]
