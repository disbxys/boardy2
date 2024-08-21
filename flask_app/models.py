from typing import List

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


# Association Table for many-to-many relationship between Image and Tag
image_tag = db.Table(
    "image_tag",
    db.Column("image_id", db.Integer, db.ForeignKey("image.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tag.id"), primary_key=True)
)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String, nullable=True)
    tags = db.relationship("Tag", backref="category")

    def __repr__(self) -> str:
        return f"Category <{self.name}> - {self.description[:20]}"
    

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String, nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=True)

    def __repr__(self) -> str:
        if self.category_id is not None:
            return f"Tag <{self.category.name}:{self.name}> - {self.description[:20]}"
        else:
            return f"Tag <{self.name}> - {self.description[:20]}"


class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), unique=True, nullable=False)
    is_video = db.Column(db.Boolean, nullable=False, default=False)

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