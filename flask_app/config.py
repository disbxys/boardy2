import os

class Config:
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024 * 1024    # 1 GB

    SECRET_KEY = "super secret key"

    # Setup internal database directory
    internal_db_path = os.path.join(os.getcwd(), "db")
    os.makedirs(internal_db_path, exist_ok=True)
    
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(internal_db_path, 'image_database.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(internal_db_path, "image_files")
    THUMBNAIL_FOLDER = os.path.join(internal_db_path, "thumbnails")
