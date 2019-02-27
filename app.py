from backend import app


if __name__ == '__main__':
    _app = app.create_app()
    _app.run(host='0.0.0.0', port=8080, debug=True)
