from waitress import serve
import app
serve(app.app, host='192.168.17.128', port=8000)


