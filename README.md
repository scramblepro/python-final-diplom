### Сервис заказов для розничных сетей
## Назначение
Backend-приложение на Django Rest Framework для автоматизации закупок розничными клиентами у поставщиков.

## Основной функционал
Регистрация и подтверждение аккаунта по email
Авторизация по токену
Управление контактами клиента
Просмотр магазинов, категорий, товаров
Формирование и оформление заказов
Управление корзиной
Поставщик может загружать прайс-лист в формате JSON/YAML
Email-уведомления клиенту и администратору
Документация API (Swagger/OpenAPI)

## Быстрый запуск (через Docker)

В проекте находятся следующие ключевые файлы для Docker:

── Dockerfile
── docker-compose.yml
── requirements.txt
── ...

## Инструкция

Клонируйте репозиторий:

git clone https://github.com/scramblepro/python-final-diplom.git
cd python-final-diplom

Соберите и запустите контейнер:

docker-compose up --build
Приложение будет доступно по адресу:
http://localhost:8000

## Ручной запуск (без Docker)

Создайте виртуальное окружение и активируйте его:

python -m venv venv
source venv/bin/activate

Установите зависимости:

pip install -r requirements.txt

Выполните миграции и создайте суперпользователя:

python manage.py migrate
python manage.py createsuperuser

Запустите сервер:

python manage.py runserver

## Примеры API-запросов

Готовые примеры находятся в файле:

requests.http

Вы можете открыть его в VSCode или использовать Postman.

## Документация API

Swagger: /swagger/

## Используемые технологии

Python 3.12

Django 5.2

Django REST Framework

SQLite

Mailtrap (SMTP)

Docker + Docker Compose

drf-spectacular (Swagger/OpenAPI)

## Примечания

По умолчанию email-уведомления отправляются через Mailtrap (тестовая SMTP-песочница)

Поддерживаются форматы импорта JSON и YAML

В проекте реализована архитектура с Signal'ами и email-рассылкой

## Автор

Насыров А. Р.
Проект для курса "[Python-разработчик]" от Нетологии
GitHub: https://github.com/scramblepro/python-final-diplom
