Nginx + Certbot

1) Ensure api.filterai.uz DNS A record points to this server.
2) Start services with docker compose.
3) Request certificate:
   docker compose run --rm certbot certonly      --webroot -w /var/www/certbot      -d api.filterai.uz      --email your-email@example.com --agree-tos --no-eff-email

Then reload nginx:
   docker compose exec nginx nginx -s reload
