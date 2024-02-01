from datetime import datetime
import hashlib
import mimetypes
import os
from typing import List, Optional

from flask import abort, request, redirect, url_for, send_from_directory, render_template

from flask_app import app
from flask_app.models import db, Image, image_tag, Tag


@app.route("/")
def index():
    rows_per_page = 42

    page = request.args.get("page", 1, type=int)

    images_query = Image.query.order_by(Image.id.desc())
    images = images_query.paginate(page=page, per_page=rows_per_page)

    return render_template("index.html", images=images)


@app.route("/delete/<int:id>")
def delete_image(id):
    image = get_image_from_db(id)
    
    if not image:
        abort(404)

    image_path = os.path.join(get_image_dir(image.filename), image.filename)

    # Delete image from file system
    os.remove(image_path)

    # Delete image from database
    db.session.delete(image)
    db.session.commit()

    return redirect(url_for("index"))


@app.route("/images/<int:id>")
def get_image(id):
    image = get_image_from_db(id)

    img_dir = os.path.normpath(os.path.join(
        app.config["UPLOAD_FOLDER"],
        get_image_dir(image.filename)
    ))

    return send_from_directory(img_dir, image.filename)


@app.route("/posts/<int:id>")
def get_image_post(id):
    image_stats = get_image_stats(id)
    image = Image.query.filter_by(id=image_stats["id"]).first()

    if image:
        tags_for_image = image.tags

        tag_info_list = []

        for tag in tags_for_image:
            # Get the number of images associated with each tag
            num_images = len(tag.images)

            tag_info_list.append((tag, num_images))

    return render_template("post.html", image_stats=image_stats, tags=tag_info_list)


@app.route("/tags")
def get_tags():
    tags = Tag.query.all()

    return {"tags": [tag.name for tag in tags]}

@app.route("/tags/images")
def get_images_by_tags():
    tags_string = request.args.get("tags", "")
    tags = Tag.query.filter(Tag.name.in_(tags_string.split())).all()

    query = db.session.query(Image)\
        .join(image_tag, image_tag.c.image_id == Image.id)\
        .join(Tag, Tag.id == image_tag.c.tag_id)
    
    for tag in tags:
        query = query.filter(Tag.name.ilike(f"%{tag.name}%"))


    return {"images": [image.filename for image in (query.all() or list())]}


@app.route("/upload", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        if "file" not in request.files:
            return redirect(url_for("index"))
        
        files = request.files.getlist("file")

        if (len(files) == 0) or (files[0].filename == ""):
            return redirect(url_for("index"))

        with db.session.no_autoflush as db_session:

            # temp: TODO: implement tag function
            tag = Tag.query.filter_by(name="general_default").first()
            if not tag:
                tag = Tag(name="general_default")

            files_saved = list()
            for file in files:
                #  Calculate file hash to use as new filename
                file_hash = sha256_hash_image_data(file.stream.read())

                file_stem, file_ext = os.path.splitext(file.filename)
                # Handle edgecase such as '.jpg' as the entire filename
                if file_ext == "":
                    file_ext = file_stem

                # Enforce allowed file upload extensions
                if file_ext not in app.config["UPLOAD_EXTENSIONS"]:
                    continue

                # Create new filename using file hash and keep extension
                new_filename = file_hash + file_ext

                # Create a save path based on file hash
                image_dir = get_image_dir(file_hash)
                save_path = os.path.join(image_dir, new_filename)

                # Do not process images already saved or duplicates
                # It should be safe to assume that if the image does not
                # exist in the file system then it also should not exist
                # in the database. Therefore, we do not need to worry about
                # UNIQUE filename constraint errors.
                if os.path.exists(save_path):
                    app.logger.warning(f"ImageExistsError: {file.filename}")
                    continue

                # Save image to filesystem
                os.makedirs(image_dir, exist_ok=True)
                file.seek(0)    # reset seek header
                # file.save(os.path.join(save_path, new_filename))
                with open(save_path, "wb") as outfile:
                    while True:
                        chunk = file.stream.read(8192)
                        if not chunk:
                            break
                        outfile.write(chunk)
                app.logger.info(f"New image saved to database: {new_filename}")

                ####
                image = Image(filename=new_filename)
                image.tags.append(tag)

                files_saved.append(image)

            db_session.add_all(files_saved)
            db_session.commit()

        return redirect(url_for("index"))
    return render_template("upload.html")


def get_image_from_db(id: int) -> Image:
    image = Image.query.filter_by(id=id).first()

    # I have no idea why favicon.ico randomly gets
    # inserted into the db. Just ignore it
    if image.filename == "favicon.ico":  abort(404)

    return image
    

def sha256_hash_image_data(image_data: bytes) -> str:
    return hashlib.sha256(image_data).hexdigest()


def get_image_dir(filename: str) -> str:
    return os.path.normpath(os.path.join(
        app.config["UPLOAD_FOLDER"],
        f"{filename[:2]}/{filename[2:4]}"
    ))


def get_image_stats(id: int) -> dict:
    image = get_image_from_db(id)

    # read image metadata from file system
    image_path = os.path.join(
        get_image_dir(image.filename),
        image.filename
    )

    # get last updated datetime
    istats = os.stat(image_path)
    i_mtime = datetime.fromtimestamp(istats.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

    # Get image type
    mtype, _ = mimetypes.guess_type(image_path)

    image_stats = {
        "id": image.id,
        "name": image.filename,
        "date": i_mtime,
        "mimetype": mtype.split("/")[1].upper() if mtype else "Unknown"
    }

    return image_stats


def search_tags(keyword: str) -> List[Tag]:
    '''Returns a list of matching tags from querying the keyword.'''
    # TODO: Add image count for each tag result
    matching_tags = Tag.query.filter(Tag.name.like(f"%{keyword}%")).all() or list()


    return [(tag, len(tag.images)) for tag in matching_tags]


def search_exact_tag(keyword: str) -> Tag:
    '''Returns an exact match for a Tag or none.'''
    # TODO: Add image count for each tag result
    return Tag.query.filter_by(name=keyword).first()


# def search_images_by_tags(tags: List[Tag]) -> List[Image]:
#     query = db.session.query(Image)\
#         .join(image_tag, image_tag.c.image_id == Image.id)\
#         .join(Tag, Tag.id == image_tag.c.tag_id)
    
#     for tag in tags:
#         query = query.filter(Tag.name.ilike(f"%{tag.name}%"))

#     return query.all() or list()