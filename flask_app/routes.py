from datetime import datetime
import hashlib
import magic
import os
from typing import List

from flask import (
    abort, jsonify, redirect, render_template, request,
    send_from_directory, url_for
)
from PIL import Image as PILImage

from flask_app import app
from flask_app.models import db, Image, image_tag, Tag


ROWS_PER_PAGE = 42


@app.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    tags_string = request.args.get("tags", "")
    
    tags = Tag.query.filter(Tag.name.in_(tags_string.split())).all()
    
    if (tags_string != "") and (len(tags) == 0):
        # No valid tags where found and the tags arg was not empty
        query = db.session.query(Image).filter_by(id=None)
    else:
        # Create the start of the search query string
        query = db.session.query(Image)\
            .join(image_tag, image_tag.c.image_id == Image.id)\
            .join(Tag, Tag.id == image_tag.c.tag_id)

        # Add an AND = clause for each tag
        for tag in tags:
            query = query.filter(Tag.name == tag.name)

        query = query.order_by(Image.id.desc())

    images = query.paginate(page=page, per_page=ROWS_PER_PAGE)

    return render_template("index.html", images=images)


@app.route("/delete/<int:id>", methods=["GET", "DELETE"])
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

    # Delete thumbnail if it exists
    thumbnail_path = get_thumbnail_filepath(image.filename)
    print(thumbnail_path)
    if os.path.exists(thumbnail_path):
        os.remove(thumbnail_path)

    return redirect(url_for("index"))


@app.route("/images/<int:id>")
def get_image(id):
    image = get_image_from_db(id)

    if os.path.exists(get_thumbnail_filepath(image.filename)):

        thumbnail_dir = get_thumbnail_dir(image.filename)
        thumbnail_filename = f"sample_{image.filename}"

        return send_from_directory(thumbnail_dir, thumbnail_filename)

    else:
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


@app.route("/tags/suggestions")
def tag_suggestions():
    query = request.args.get("q", "")

    tags = Tag.query\
        .filter(Tag.name.ilike(f"{query}%"))\
        .order_by(Tag.name)\
        .limit(10)\
        .all()

    suggestions = [tag.name for tag in tags]
    
    return jsonify({"suggestions": suggestions})


@app.route("/tags/add/<int:image_id>", methods=["POST"])
def add_tag_to_image(image_id):
    image = Image.query.get_or_404(image_id)

    new_tag_name = request.form.get("new_tag", "").strip()
    new_tag_name = new_tag_name.replace(" ", "_")

    if new_tag_name:
        tag = Tag.query.filter_by(name=new_tag_name).first()

        if not tag:
            # Add new tag to database
            tag = Tag(name=new_tag_name)
            db.session.add(tag)

        if tag not in image.tags:
            # Add tag to image if not on image already.
            image.tags.append(tag)
            app.logger.info(f"New tag <{new_tag_name}> added for image id <{image_id}>.")
        else:
            app.logger.warning(f"Tag <{new_tag_name}> already exists for image id <{image_id}>.")

        db.session.commit()
    
    return redirect(url_for("get_image_post", id=image_id))


@app.route("/tags/<string:name>")
def get_images_by_tag(name: str):
    page = request.args.get("page", 1, type=int)

    tag = Tag.query.filter_by(name=name).first_or_404()

    query = db.session.query(Image)\
        .join(image_tag, image_tag.c.image_id == Image.id)\
        .join(Tag, Tag.id == image_tag.c.tag_id)\
        .filter(Tag.name == tag.name)\
        .order_by(Image.id.desc())
    
    images = query.paginate(page=page, per_page=ROWS_PER_PAGE)

    return render_template("tag.html", tag=tag, images=images)


@app.route("/tags/delete", methods=["DELETE"])
def remove_tags():
    """
    Take a list of tag ids and either remove them from the image
    or delete the tag entirely.
    """
    image_id = request.args.get("id")
    delete_ = request.args.get("delete", type=lambda x: x.lower() == "true")
    tags_string = request.args.get("tags")

    tags_list = [int(tag_id) for tag_id in tags_string.split(",")]
    tags = db.session.query(Tag)\
        .filter(Tag.id.in_(tags_list))\
        .all()
    
    if delete_:
        with db.session.no_autoflush as db_session:
            for tag in tags:
                db_session.delete(tag)
    else:
        image = Image.query.filter_by(id=image_id).first_or_404()
        if image and len(tags) > 0:
            image.remove_tags(tags)

    db.session.commit()

    return redirect(url_for("get_image_post", id=image_id))


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

                is_valid_upload, mimetype = is_image_file(file)

                # Enforce allowed file upload extensions
                if not is_valid_upload: continue

                # Create new filename using file hash and keep extension
                file_ext = mimetype.split("/")[1].lower()
                new_filename = f"{file_hash}.{file_ext}"

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

                # Generate a thumbnail
                thumbnail_dir = get_thumbnail_dir(new_filename)
                os.makedirs(thumbnail_dir, exist_ok=True)
                thumbnail_filename = f"sample_{new_filename}"
                thumbnail_path = os.path.join(thumbnail_dir, thumbnail_filename)
                create_thumbnail(save_path, thumbnail_path)

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


def get_thumbnail_dir(filename: str) -> str:
    return os.path.normpath(os.path.join(
        app.config["THUMBNAIL_FOLDER"],
        f"{filename[:2]}/{filename[2:4]}"
    ))


def get_thumbnail_filepath(image_filename: str) -> str:
    return os.path.normpath(os.path.join(
        get_thumbnail_dir(image_filename),
        f"sample_{image_filename}"
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
    mtype = magic.from_file(image_path, mime=True)

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


def is_image_file(file):
    """
    Returns True if file is an image.

    This relies on the accuracy of python magic.
    """
    file.seek(0)    # Reset seek header
    mime_type = magic.from_buffer(file.read(2048), mime=True)
    file.seek(0)    # Reset seek header again

    return mime_type.startswith("image/"), mime_type


def create_thumbnail(input_path: str, output_path: str, max_size = (650, 650)):
    with PILImage.open(input_path) as img:
        img.thumbnail(max_size)
        img.save(output_path)
