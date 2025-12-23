#!/bin/sh
set -e

INIT_FLAG="/app/.initialized"

if [ ! -f "$INIT_FLAG" ]; then
    echo "🚀 Перший запуск контейнера. Виконую початкове налаштування..."

    python manage.py migrate --noinput
    python manage.py collectstatic --noinput

    python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email="adm@adm.com").exists():
    User.objects.create_superuser(email="adm@adm.com", password="admin123", first_name="Адмін", last_name="Адмінич")
    User.objects.create_user(email="yuliia@adm.com", password="admin123", first_name="Юлія", last_name="Петрівна")
    User.objects.create_user(email="paladin@adm.com", password="admin123", first_name="Валентин", last_name="Миколайович")
    print("Superuser created (adm@adm.com)")
else:
    print("Superuser already exists.")
END

    python manage.py import_employee
    python manage.py mark_status

    touch "$INIT_FLAG"
    echo "✔️ Ініціалізація завершена. Файл-прапор створено."
else
    echo "➡️ Повторний запуск контейнера – пропускаю ініціалізацію."
fi

echo "🔧 Запуск Gunicorn..."
exec gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 5 --threads 2 --timeout 300 --preload
