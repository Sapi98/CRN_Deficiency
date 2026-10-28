"""Production entry point: gunicorn web.wsgi:server."""
from web.app import create_app

app = create_app()
server = app.server
