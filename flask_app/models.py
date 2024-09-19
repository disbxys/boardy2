from enum import Enum
from typing import List

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Enum as SqlEnum


db = SQLAlchemy()


class TagCategory(Enum):
    COPYRIGHT = "copyright"
    CHARACTER = "character"
    ARTIST = "artist"
    GENERAL = "general"
    METADATA = "metadata"


    @classmethod
    def of(cls, value: str) -> "TagCategory":
        value = value.strip().upper()
        for category in cls:
            if category.name == value:
                return category

        # I would rather throw an exception here but I figured that
        # it would be better to just default to general.
        raise cls.GENERAL


# Association Table for many-to-many relationship between Image and Tag
image_tag = db.Table(
    "image_tag",
    db.Column("image_id", db.Integer, db.ForeignKey("image.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tag.id"), primary_key=True)
)


class Tag(db.Model):
    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String(50), unique=True, nullable=False)
    category: TagCategory = db.Column(SqlEnum(TagCategory), nullable=False, default=TagCategory.GENERAL)
    description: str = db.Column(db.String, nullable=True)


    def __init__(
            self,
            name: str,
            category: TagCategory | str = TagCategory.GENERAL,
            description: str | None = None
    ):
        self.name = name
        self.description = description

        if isinstance(category, str):
            self.category = TagCategory.of(category)
        else:
            self.category = category
        print(self.category)


    def __repr__(self) -> str:
        return f"Tag <{self.category.name}:{self.name}>"


class Image(db.Model):
    id: int = db.Column(db.Integer, primary_key=True)
    filename: str = db.Column(db.String(255), unique=True, nullable=False)
    is_video: bool = db.Column(db.Boolean, nullable=False, default=False)

    # Define the many-to-many relationship with Tag
    tags = db.relationship("Tag", secondary=image_tag, backref="images")

    def __repr__(self) -> str:
        return f"Image <{self.filename}>"

    def remove_tags(self, tags_to_remove: List[Tag]) -> None:
        for tag in tags_to_remove:
            if tag in self.tags:
                self.tags.remove(tag)


# Call configure on the registry
db.configure_mappers()