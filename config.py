class Config:
    DEBUG = True
    TESTING = False
    SECRET_KEY = "dev-secret-key"


class TestingConfig(Config):
    TESTING = True


