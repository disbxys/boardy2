import os

class Config:
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024 * 1024    # 1 GB

    SECRET_KEY = "super secret key"

    SQLALCHEMY_DATABASE_URI = "sqlite:///image_database.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(os.getcwd(), "db", "image_files")
    THUMBNAIL_FOLDER = os.path.join(os.getcwd(), "db", "thumbnails")
