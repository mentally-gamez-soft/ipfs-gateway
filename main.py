from core import create_app


app = create_app()


def main():
    # Determine host based on environment
    app_env = app.config.get("APP_ENV", "development")
    host = "0.0.0.0" if app_env in ["staging", "production"] else "127.0.0.1"
    
    app.run(host=host, port=5000)


if __name__ == "__main__":
    main()
