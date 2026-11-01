# # # project/__init__.py

from decouple import config

# N'active le driver MySQL que si DB_ENGINE=mysql dans .env (prod cPanel).
# En dev local (DB_ENGINE=postgresql, valeur par defaut), pymysql n'est pas
# requis et ne doit pas etre importe : evite de casser `runserver` en local.
if config('DB_ENGINE', default='postgresql').strip().lower() == 'mysql':
    import pymysql

    pymysql.install_as_MySQLdb()