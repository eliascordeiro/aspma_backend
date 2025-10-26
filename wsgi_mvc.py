from app_mvc import create_app

# WSGI entrypoint for the MVC refactored application (with Swagger)
app = create_app()

if __name__ == '__main__':
    # Development run
    app.run(host='0.0.0.0', port=5000)
