## Изучите [README.md](.\README.md) файл и структуру проекта.

# Задание 1

### 1. Описание функциональности приложения

- Cтриминговый сервис, где пользователи могут посмотреть контент из других сервисов и открытых источников по единой подписке.
- Пользователь открывает сайт, аутентифицируется, выбирает фильм, может оценить фильм и составить папку с избранным.
- Сторонняя рекомендательная система делает подборку.
- Клиенты сервиса используют мобильные устройства, ноутбуки, смарт ТВ. Как следствие, на разных девайсах различаются интерфейсы и количество данных.

### 2. Анализ архитектуры монолитного приложения

- Все вызовы за исключением взаимодействия с рекомендательной системой происходят синхронно. 
- API компании построено в соответствии с REST-стилем.
- Сущности в базе: платежи, пользователи, видео, подписки, скидки, метаданные о фильмах (жанры, актёры, оценки).
- Большой и запутанный монолит на Go c СУБД PostgreSQL (одна база данных).


### 3. Определение доменов и границы контекстов
- Система: Cтриминговый сервис Cinemaabyss.

- Домен 1: Movies Service 
    - контекст: управление сущностью "фильмы" (CRUD):
        - Метаданные фильмов;
        - Рейтинги;
        - Жанры.
   
- Домен 2: Events Service
Обрабатывает  :
    - контекст: коммуникацию между сервисами на основе событий с использованием Kafka:
        - События фильмов (просмотр, оценка, добавление);
        - События пользователей (регистрация, вход);
        - События платежей (успешные, неудачные).

- Домен 3: Proxy Service (API Gateway)
    - контекст: маршрутизирует запросы;
    - контекст: шлюз между front, внешними систмами и back-end

- Домен 4: Управление пользователями и администраторами
    - контекст: регистрация пользователей
    - контекст: аутентификация и авторизация

- Домен 5: Управление подпиской
    - контекст: CRUD/конфигуратор
    - контекст: параметры подписки

- Домен 6:  Взаимодействие с пользователями
    - контекст: выбор фильма, оценка, составить папку с избранным;
    - учет специфики устройства пользователя (мобильные устройства, ноутбуки, смарт ТВ). 

- Домен 7: Внешние системы:
    - контекст: Платежная система
    - контекст: Рекомендательная система

[Диаграмма контейнеров](https://github.com/rusjiu-dev/architecture-cinemaabyss/tree/cinema/doc/arch_containers_C4.puml)

# Задание 2

### 1. Proxy
- После реализации запустите postman тесты - они все должны быть зеленые (кроме events).

[Результаты тестов](https://github.com/rusjiu-dev/architecture-cinemaabyss/blob/cinema/doc/Postman_task_2_1.png)

- Отправьте запросы к API Gateway:
   ```bash
   curl http://localhost:8000/api/movies
   ```

[Ответ](https://github.com/rusjiu-dev/architecture-cinemaabyss/blob/cinema/doc/curl.png)

- Протестируйте постепенный переход, изменив переменную окружения MOVIES_MIGRATION_PERCENT в файле docker-compose.yml.

[MOVIES_MIGRATION_PERCENT: "90"](https://github.com/rusjiu-dev/architecture-cinemaabyss/blob/cinema/doc/migration_rate_90.png)

### 2. Kafka
Необходимые тесты для проверки этого API вызываются при запуске npm run test:local из папки tests/postman 

[Результаты тестов](https://github.com/rusjiu-dev/architecture-cinemaabyss/blob/cinema/doc/task2_tests.png)

Приложите скриншот тестов и скриншот состояния топиков Kafka из UI http://localhost:8090 

[Kafka topics](https://github.com/rusjiu-dev/architecture-cinemaabyss/blob/cinema/doc/task2_topics.png)

# Задание 3

### CI/CD

Как только сборка отработает и в github registry появятся ваши образы, можно переходить к блоку настройки Kubernetes
Успешным результатом данного шага является "зеленая" сборка и "зеленые" тесты

[Сборка](https://github.com/rusjiu-dev/architecture-cinemaabyss/blob/cinema/doc/actions_build.png)

[Тесты](https://github.com/rusjiu-dev/architecture-cinemaabyss/blob/cinema/doc/actions_tests.png)


### Proxy в Kubernetes

Добавьте сюда скриншота вывода при вызове https://cinemaabyss.example.com/api/movies и  скриншот вывода event-service после вызова тестов.

[Вызов api/movies](https://github.com/rusjiu-dev/architecture-cinemaabyss/blob/cinema/doc/task3_movies_get.png)

[Логи event-service](https://github.com/rusjiu-dev/architecture-cinemaabyss/blob/cinema/doc/event_logs.png)

# Задание 4
Для простоты дальнейшего обновления и развертывания вам как архитектуру необходимо так же реализовать helm-чарты для прокси-сервиса и проверить работу 

Для этого:
1. Перейдите в директорию helm и отредактируйте файл values.yaml

```yaml
# Proxy service configuration
proxyService:
  enabled: true
  image:
    repository: ghcr.io/db-exp/cinemaabysstest/proxy-service
    tag: latest
    pullPolicy: Always
  replicas: 1
  resources:
    limits:
      cpu: 300m
      memory: 256Mi
    requests:
      cpu: 100m
      memory: 128Mi
  service:
    port: 80
    targetPort: 8000
    type: ClusterIP
```

- Вместо ghcr.io/db-exp/cinemaabysstest/proxy-service напишите свой путь до образа для всех сервисов
- для imagePullSecret проставьте свое значение (скопируйте из конфигурации kubernetes)
  ```yaml
  imagePullSecrets:
      dockerconfigjson: ewoJImF1dGhzIjogewoJCSJnaGNyLmlvIjogewoJCQkiYXV0aCI6ICJaR0l0Wlhod09tZG9jRjl2UTJocVZIa3dhMWhKVDIxWmFVZHJOV2hRUW10aFVXbFZSbTVaTjJRMFNYUjRZMWM9IgoJCX0KCX0sCgkiY3JlZHNTdG9yZSI6ICJkZXNrdG9wIiwKCSJjdXJyZW50Q29udGV4dCI6ICJkZXNrdG9wLWxpbnV4IiwKCSJwbHVnaW5zIjogewoJCSIteC1jbGktaGludHMiOiB7CgkJCSJlbmFibGVkIjogInRydWUiCgkJfQoJfSwKCSJmZWF0dXJlcyI6IHsKCQkiaG9va3MiOiAidHJ1ZSIKCX0KfQ==
  ```

2. В папке ./templates/services заполните шаблоны для proxy-service.yaml и events-service.yaml (опирайтесь на свою kubernetes конфигурацию - смысл helm'а сделать шаблоны для быстрого обновления и установки)

```yaml
template:
    metadata:
      labels:
        app: proxy-service
    spec:
      containers:
       Тут ваша конфигурация
```

3. Проверьте установку
Сначала удалим установку руками

```bash
kubectl delete all --all -n cinemaabyss
kubectl delete  namespace cinemaabyss
```
Запустите 
```bash
helm install cinemaabyss .\src\kubernetes\helm --namespace cinemaabyss --create-namespace
```
Если в процессе будет ошибка
```code
[2025-04-08 21:43:38,780] ERROR Fatal error during KafkaServer startup. Prepare to shutdown (kafka.server.KafkaServer)
kafka.common.InconsistentClusterIdException: The Cluster ID OkOjGPrdRimp8nkFohYkCw doesn't match stored clusterId Some(sbkcoiSiQV2h_mQpwy05zQ) in meta.properties. The broker is trying to join the wrong cluster. Configured zookeeper.connect may be wrong.
```

Проверьте развертывание:
```bash
kubectl get pods -n cinemaabyss
minikube tunnel
```

Потом вызовите 
https://cinemaabyss.example.com/api/movies
и приложите скриншот развертывания helm и вывода https://cinemaabyss.example.com/api/movies

## Удаляем все

```bash
kubectl delete all --all -n cinemaabyss
kubectl delete namespace cinemaabyss
```
