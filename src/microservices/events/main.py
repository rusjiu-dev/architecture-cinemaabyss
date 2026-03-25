import os
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.errors import KafkaError

# Конфигурация
KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "kafka:9092")
TOPICS = {
    "movie": "movie-events",
    "user": "user-events",
    "payment": "payment-events"
}

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("events-service")

# Глобальные объекты
producer = None
consumer_tasks = []


async def start_consumer(topic: str):
    """Запуск консьюмера для конкретного топика."""
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=KAFKA_BROKERS,
        group_id="events-service-group",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )
    await consumer.start()
    logger.info(f"Consumer started for topic: {topic}")
    try:
        async for msg in consumer:
            try:
                value = json.loads(msg.value.decode("utf-8"))
                logger.info(f"Consumed from {topic}: {value}")
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    finally:
        await consumer.stop()


async def produce_event(topic: str, event_data: dict):
    """Публикация события в Kafka."""
    if producer is None:
        raise RuntimeError("Producer not initialized")
    try:
        await producer.send_and_wait(topic, json.dumps(event_data).encode("utf-8"))
        logger.info(f"Produced to {topic}: {event_data}")
    except KafkaError as e:
        logger.error(f"Kafka error: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом: запуск продюсера и консьюмеров."""
    global producer, consumer_tasks
    
    # Запуск продюсера
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BROKERS)
    await producer.start()
    logger.info("Kafka producer started")
    
    # Запуск консьюмеров для каждого топика
    for topic_name, topic in TOPICS.items():
        task = asyncio.create_task(start_consumer(topic))
        consumer_tasks.append(task)
    
    yield
    
    # Остановка продюсера и консьюмеров
    if producer:
        await producer.stop()
    for task in consumer_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    logger.info("Shutdown complete")


app = FastAPI(title="Events Service", lifespan=lifespan)


@app.get("/api/events/health")
async def health():
    """Проверка работоспособности."""
    return {"status": True}


@app.post("/api/events/movie")
async def create_movie_event(request: Request):
    """
    Создание события фильма.
    Ожидает тело запроса: { movie_id, title, action, user_id?, rating?, genres?, description? }
    """
    data = await request.json()
    required_fields = ["movie_id", "title", "action"]
    for field in required_fields:
        if field not in data:
            return JSONResponse(
                status_code=400,
                content={"error": f"Missing required field: {field}"}
            )
    await produce_event(TOPICS["movie"], data)
    return JSONResponse(
        status_code=201,
        content={
            "status": "success",
            "partition": 0,
            "offset": 0,
            "event": {
                "id": f"movie-{data['movie_id']}-{data['action']}",
                "type": "movie",
                "timestamp": "2024-01-01T00:00:00Z",  # фактическое время можно добавить
                "payload": data
            }
        }
    )


@app.post("/api/events/user")
async def create_user_event(request: Request):
    """
    Создание события пользователя.
    Ожидает тело запроса: { user_id, action, timestamp, username?, email? }
    """
    data = await request.json()
    required_fields = ["user_id", "action", "timestamp"]
    for field in required_fields:
        if field not in data:
            return JSONResponse(
                status_code=400,
                content={"error": f"Missing required field: {field}"}
            )
    await produce_event(TOPICS["user"], data)
    return JSONResponse(
        status_code=201,
        content={
            "status": "success",
            "partition": 0,
            "offset": 0,
            "event": {
                "id": f"user-{data['user_id']}-{data['action']}",
                "type": "user",
                "timestamp": data["timestamp"],
                "payload": data
            }
        }
    )


@app.post("/api/events/payment")
async def create_payment_event(request: Request):
    """
    Создание события платежа.
    Ожидает тело запроса: { payment_id, user_id, amount, status, timestamp, method_type? }
    """
    data = await request.json()
    required_fields = ["payment_id", "user_id", "amount", "status", "timestamp"]
    for field in required_fields:
        if field not in data:
            return JSONResponse(
                status_code=400,
                content={"error": f"Missing required field: {field}"}
            )
    await produce_event(TOPICS["payment"], data)
    return JSONResponse(
        status_code=201,
        content={
            "status": "success",
            "partition": 0,
            "offset": 0,
            "event": {
                "id": f"payment-{data['payment_id']}",
                "type": "payment",
                "timestamp": data["timestamp"],
                "payload": data
            }
        }
    )