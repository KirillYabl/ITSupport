# Название проекта и описание

## Цель проекта

## Как установить

Должны быть установлены следующие программы
1. Python 3.9+

В папке `./it_support/it_support` создать файл `.env` со следующим содержанием:

```text
DJANGO_SECRET_KEY=REPLACE_ME
```

Для запуска телеграм бота необходимо прописать в `.env` его `токен`:

```text
TELEGRAM_ACCESS_TOKEN=
```

Создать виртуальное окружение в корневой папке проекта

```shell
python -m venv venv
```

Установить зависимости

```shell
pip install -r requirements.txt
```

Перейти в папку `it_support` и выполнить миграции

```shell
cd ./it_support
python manage.py migrate
```

## Как запустить

Выполнить команду из папки `it_support` относительно корневой папки проекта

```shell
python manage.py runserver
```
Для запуска бота выполнить команду:

```shell
python manage.py start_bot
```

## Цели проекта

Код написан в учебных целях — это командный проект в курсе по Python и веб-разработке на
сайте [Devman](https://dvmn.org).