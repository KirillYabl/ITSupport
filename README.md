# Сервис ITSupport

Это телеграм бот, клиенты которого могут заказывать быструю помощь по 
поддержке, а база из заказчиков может забирать заказы

В боте есть 4 роли:
1. Клиент - тот, кому нужна техническая помощь, у него есть тариф с ограничением 
заказов, доп функциями и временем реакции оплата вне бота
ЗДЕСЬ_ГИФКА_ПРОЦЕССА
2. Подрядчик - тот, кто оказывает тех помощь, ставка за заказ задается в админке, оплата подрядчикам вне бота
ЗДЕСЬ_ГИФКА_ПРОЦЕССА
3. Владелец - админ бота, может добавлять пользователей, а также просматривать отчеты
ЗДЕСЬ_ГИФКА_ПРОЦЕССА
4. Менеджер - предупреждается если заказ долго выполняется или не берется в 
работу, может получить список свободных заказчиков, чтобы связаться с ними и попросить взять заказ
ЗДЕСЬ_ГИФКА_ПРОЦЕССА

Также есть web интерфейс администратора для настройки тарифов и управления системными параметрами

## Как установить

Должны быть установлены следующие программы
1. Python 3.9+

В папке `./it_support/it_support` создать файл `.env` со следующим содержанием:

```text
DJANGO_SECRET_KEY=REPLACE_ME
TELEGRAM_ACCESS_TOKEN=SECRET_TOKEN
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

## Как запустить dev версию

Выполнить команду из папки `it_support` относительно корневой папки проекта

Для запуска панели администратора

```shell
python manage.py runserver
```
Для запуска бота выполнить команду:

```shell
python manage.py start_bot
```

## Как запустить prod версию

Проект скачиваем в директорию `/opt`.

Устанавливаем все необходимые зависимости. (см. пункт `Как установить`)

Также после сделанной миграции вам неободимо подтянуть всю статику командой:

```
python manage.py collectstatic
```

Параметры запуска проекта через systemctl смотрите ниже:
* Файл для запуска самой Django:
```
[Unit]
Description=Django for Telegram bot

[Service]
WorkingDirectory=/opt/ITSupport/it_support
ExecStart=/opt/ITSupport/venv/bin/gunicorn -w 3 -b 127.0.0.1:8100 it_support.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```
* Файл для запуска бота:

```
[Unit]
Description=Telegram bot on Django
Requires=django_bot.service

[Service]
WorkingDirectory=/opt/ITSupport/it_support
ExecStart=/opt/ITSupport/venv/bin/python3 manage.py start_bot
Restart=always

[Install]
WantedBy=multi-user.target
```
Параметры Nginx:
```
server {
  listen 11.111.111.111:80;  # Вместо единиц укажите ip вашего сервера  

  location / {
    include '/etc/nginx/proxy_params';
    proxy_pass http://127.0.0.1:8100/;
  }

  location /static/ {
    alias /opt/ITSupport/it_support/staticfiles/;
  }
}
```
Уже после данных настроек можно всё активировать и пользоваться админкой на удаленном сервере.

## Системные параметры

Системные параметры управляют поведением бота, внести их и изменить можно в админ модели по адресу /admin/support_app/systemsettings/

1. `ASSIGNED_CONTRACTORS_TIME_LIMIT` (default=20) - Процент (от 1 до 100 целое число) времени, которое должно пройти от взятия создания заказа до планового времени реакции на тарифе чтобы начать информировать остальных подрядчиков о новом заказе, а не только закрепленных
2. `INFORM_MANAGER_IN_WORK_PROJECT_LIMIT` (default=95) - Процент (от 1 до 100 целое число) времени, которое должно пройти от взятия создания заказа до планового времени реакции на тарифе чтобы начать информировать остальных подрядчиков о новом заказе, а не только закрепленных
3. `INFORM_MANAGER_CREATED_PROJECT_LIMIT` (default=95) - Процент (от 1 до 100 целое число) времени, которое должно пройти от создания заказа до времени реакции на тарифе, чтобы начать информировать менеджера о том, что созданный заказ долго не берут
4. `BILLING_DAY` (default=1) - Дата ежемесячного биллинга, должна быть от 1 до 28 включительно (больше могут быть ошибки). Т.е. биллинг начинается с BILLING_DAY каждого месяца по BILLING_DAY следующего
5. `ORDER_RATE` (default=500) - ставка за выполнения заказа в рублях

## Улучшения и исправления на будущее

### Технический долг

1. Разобраться со всеми TODO в коде
   - Шифрование и дешифрование доступов к сайтам клиентов
   - Сохранение нужных данных в бота до старта (примеры заявок и т.д.)
   - Оптимизация и сокращение некоторых запросов
   - Работа с эстимейтами при поиске проектов, которые долго берутся в работу, вместо фиксированной цифры
2. Переехать на ConversationalHandler, что бы логику похожих кнопок меньше описывать в других состояниях
3. Покрыть код тестами
4. Профилировать и оптимизировать количество совершаемых запросов
5. Логирование
6. Мониторинг
7. Переезд на postgres
8. Упаковка в контейнеры

### Функциональность

1. Добавить возможность общаться подрядчику и клиенту не только текстом, а также документами, фото и голосовыми
2. Добавить возможность подрядчику работать с несколькими заказами
3. Добавить возможность клиенту оставлять несколько заказов
4. Добавить возможность управления тарифами владельцу через бота
5. Добавить возможность изменения тарифа клиента владельцу через бота
6. Интеграция оплаты (сама оплата, история цен тарифов, фиксирование стоимостей за период, баланс, задания по биллингу и т.д. и т.д.)
7. Удаление некоторых сообщений ботом при общении (например старых меню)
8. Сохранение переписки между клиентами и подрядчиками

## Цели проекта

Код написан в учебных целях — это командный проект в курсе по Python и веб-разработке на
сайте [Devman](https://dvmn.org).