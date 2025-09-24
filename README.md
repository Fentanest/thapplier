Usage
=

`docker pull fentanest/topheroes-applier:latest`

Docker Compose(Example)
-
```
services:
  topheroes-applier-instance:
    image: fentanest/topheroes-applier:latest
    container_name: topheroes-applier-instance
    ports:
      - "5001:5001"
    environment:
      SELENIUM_HUB_URL: "http://192.168.50.1:4444"
      MAX_CONCURRENT_SESSIONS: 10
      DELAY_BETWEEN_SESSIONS: 10
      AUTH_USERNAME: username
      AUTH_PASSWORD: password
      TZ: Asia/Seoul
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
      TELEGRAM_CHAT_ID: ${TELEGRAM_CHAT_ID}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./coupon_logs:/app/coupon_logs
    restart: always

```

Environments
-

|Environments|Defaults|Explain|
|---|---|---|
|`TELEGRAM_BOT_TOKEN`|none|need if you want to operate Telegram bots for this application|
|`TELEGRAM_CHAT_ID`|none|need if you want to operate Telegram bots for this application|
|`SELENIUM_HUB_URL`|`http://localhost:4444`|put Selenium Hub URL here|
|`MAX_CONCURRENT_SESSIONS`|`1`|determine the max sessions to run stimultaneously. need same amount of chrome sessions in Selenium Hub|
|`DELAY_BETWEEN_SESSIONS`|`10`|To avoid errors, need to set a delay time between sessions|
|`BASE_URL`|`https://topheroes.store.kopglobal.com/ko/`|Base URL for TopHeroes store, No need to modify unless there are special circumstances|
|`AUTH_USERNAME`|`topheroes`|Username for Web UI authentication|
|`AUTH_PASSWORD`|`applier`|Password for Web UI authentication|
|`TZ`|`Asia/Seoul`|TimeZone|
