# Настройка HTTPS для payment.egeinformatika.ru

Домен `payment.egeinformatika.ru` → A-запись → `5.129.203.166`
Nginx проксирует 80/443 → `127.0.0.1:8000` (platform-payment-sync).

## Команды

```bash
sudo apt install -y nginx certbot python3-certbot-nginx

sudo nano /etc/nginx/sites-available/payment.egeinformatika.ru
# вставить содержимое файла payment.egeinformatika.ru из этой папки

sudo ln -s /etc/nginx/sites-available/payment.egeinformatika.ru /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

sudo certbot --nginx -d payment.egeinformatika.ru
```

Certbot сам допишет блок `listen 443 ssl` и редирект с 80 на 443 в `/etc/nginx/sites-enabled/payment.egeinformatika.ru`.
Автопродление сертификата настраивается certbot'ом автоматически (systemd timer).

## Проверка

```bash
curl https://payment.egeinformatika.ru/webhook/health
```

## Итоговый адрес для платформы

```
https://payment.egeinformatika.ru/webhook/payment
```
