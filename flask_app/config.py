import os

class Config:
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024 * 1024    # 1 GB

    UPLOAD_EXTENSIONS = [".avif", ".bmp", ".gif", ".jpg", ".jpeg", ".png", ".webp"]

    SECRET_KEY = "super secret key"

    SQLALCHEMY_DATABASE_URI = "sqlite:///image_database.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(os.getcwd(), "db")