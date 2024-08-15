from datetime import datetime
import hashlib
import magic
import os
from typing import List

import cv2
from flask import (
    abort, jsonify, redirect, render_template, request,
    send_from_directory, url_for
)
from PIL import Image as PILImage
import werkzeug.datastructures.file_storage as werkzeug_fs

from flask_app import app
from flask_app.models import db, Image, image_tag, Tag


PER_PAGE = 42


@app.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    search_string = request.args.get("tags", "")

    # All keywords in the search string must be valid tags
    keywords = [x.strip() for x in search_string.split() if x.strip() != ""]
    tags = Tag.query.filter(Tag.name.in_(keywords)).all()
    
    if (search_string.strip() == ""):
        # Empty search bar means search all
        query = db.session.query(Image)
    elif len(keywords) != len(tags):
        # Not all keywords in the search string were valid tag names
        query = db.session.query(Image).filter_by(id=None)
    else:
        # Create the start of the search query string
        query = db.session.query(Image)\
            .join(image_tag, image_tag.c.image_id == Image.id)\
            .join(Tag, Tag.id == image_tag.c.tag_id)

        # Add an AND = clause for each tag
        for tag in tags:
            query = query.filter(Tag.name == tag.name)

    images = query\
        .order_by(Image.id.desc())\
        .paginate(page=page, per_page=PER_PAGE)

    return render_template("index.html", images=images, keyword=search_string, current_page=page)


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
    
    if os.path.exists(thumbnail_path):
        os.remove(thumbnail_path)

    return redirect(url_for("index"))


@app.route("/images/<int:id>")
def get_image(id):
    image = get_image_from_db(id)

    img_dir = os.path.normpath(os.path.join(
        app.config["UPLOAD_FOLDER"],
        get_image_dir(image.filename)
    ))

    return send_from_directory(img_dir, image.filename)


@app.route("/thumbnails/<int:id>")
def get_thumbnail(id):
    image = get_image_from_db(id)

    thumbnail_path = get_thumbnail_filepath(image.filename)

    thumbnail_dir, thumbnail_filename = os.path.split(thumbnail_path)

    return send_from_directory(thumbnail_dir, thumbnail_filename)


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
def tags_index():
    letter: str | None = request.args.get("letter", type=str)

    query = db.session.query(Tag)
    if letter is not None:
        if (not letter.isalnum()) and (len(letter) != 1): abort (404)

        if not letter.isalpha():
            letter = "."

        if letter == ".":
            query = query.filter(~Tag.name.op("REGEXP")(r"^[a-zA-Z]"))
        else:
            query = query.filter(Tag.name.ilike(f"{letter}%"))

    tags = query.order_by(Tag.name).all()

    return render_template("tags_index.html", tags=tags, current_letter=letter)


@app.route("/tags/suggestions")
def tag_suggestions():
    query = request.args.get("q", "")

    tags = Tag.query\
        .filter(Tag.name.ilike(f"{query}%"))\
        .order_by(Tag.name)\
        .limit(10)\
        .all()

    suggestions = [f"{tag.name} ({len(tag.images)})" for tag in tags]

    return jsonify({"suggestions": suggestions})


@app.route("/tags/add/<int:image_id>", methods=["POST"])
def add_tag_to_image(image_id):
    image = Image.query.get_or_404(image_id)
    
    new_tag_names = request.form.get("new_tag", "").split(",")
    for new_tag_name in new_tag_names:
        # Sanitize input
        new_tag_name = new_tag_name.strip().replace(" ", "_")

        if new_tag_name:
            tag = Tag.query.filter_by(name=new_tag_name).first()

            if not tag:
                # Add new tag to database
                tag = Tag(name=new_tag_name)
                db.session.add(tag)
                app.logger.info(f"New tag created: {new_tag_name}.")

            if tag not in image.tags:
                # Add tag to image if not on image already.
                image.tags.append(tag)
                app.logger.info(f"Tag <{new_tag_name}> added to image id <{image_id}>.")
            else:
                app.logger.warning(f"Tag <{new_tag_name}> already exists for image id <{image_id}>.")

            db.session.commit()
    
    return redirect(url_for("get_image_post", id=image_id))


@app.route("/tags/<string:name>")
def get_images_by_tag(name: str):
    page = request.args.get("page", 1, type=int)

    tag = Tag.query.filter_by(name=name).first_or_404()

    title = tag.name.replace("_", " ").title()

    query = db.session.query(Image)\
        .join(image_tag, image_tag.c.image_id == Image.id)\
        .join(Tag, Tag.id == image_tag.c.tag_id)\
        .filter(Tag.name == tag.name)\
        .order_by(Image.id.desc())
    
    images = query.paginate(page=page, per_page=PER_PAGE)

    return render_template("tag.html", title=title, tag=tag, images=images, current_page=page)


@app.route("/tags/delete", methods=["DELETE", "GET"])
def remove_tags():
    """
    Take a list of tag ids and either remove them from the image
    or delete the tag entirely.
    """
    image_id = request.args.get("id")
    delete_ = request.args.get("delete", type=lambda x: x.lower() == "true")
    tags_string = request.args.get("tags", "", str)

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
            general_tag = Tag.query.filter_by(name="general").first()
            if not general_tag:
                general_tag = Tag(name="general")

            video_tag = Tag.query.filter_by(name="video").first()
            if not video_tag:
                video_tag = Tag(name="video")

            files_saved = list()
            for file in files:
                #  Calculate file hash to use as new filename
                file_hash = sha256_hash_image_data(file.stream.read())

                is_valid_upload, mimetype = is_image_file(file)
                is_video = False
                if is_valid_upload is False:
                    is_valid_upload, mimetype = is_video_file(file)
                    is_video = True

                # Enforce allowed file upload extensions
                if not is_valid_upload: continue

                # Create new filename using file hash and keep extension
                file_ext = translate_mimetype_to_ext(mimetype).lower()
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

                # Save stream to file
                stream_to_file(file, save_path)
                app.logger.info(f"New image saved to database: {new_filename}")

                # Generate a thumbnail
                thumbnail_path = get_thumbnail_filepath(new_filename)
                os.makedirs(
                    os.path.dirname(thumbnail_path),
                    exist_ok=True
                )
                create_thumbnail(save_path, video = is_video)
                app.logger.info(f"Thumbnail generated for database image: {new_filename}")

                ####
                image = Image(filename=new_filename, is_video=is_video)
                image.tags.append(general_tag)
                if is_video or file_ext == "gif":
                    image.tags.append(video_tag)

                files_saved.append(image)

            db_session.add_all(files_saved)
            db_session.commit()

        return redirect(url_for("index"))
    return render_template("upload.html")


def stream_to_file(file: werkzeug_fs.FileStorage, save_path: str):
    # Ensure directory to write file to exists
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    # Reset seek header in case it has already been used.
    file.stream.seek(0)

    # Write stream to file in chunks to save resources on
    # large files.
    with open(save_path, "wb") as outfile:
        while True:
            chunk = file.stream.read(8192)
            if not chunk:
                break
            outfile.write(chunk)


def get_image_from_db(id: int) -> Image:
    image = Image.query.filter_by(id=id).first_or_404()

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


def translate_mimetype_to_ext(mtype: str) -> str:
    # Special cases where mimetype needs to be converted
    # into a valid/standardized file format
    mtype_special_cases = {
        "x-matroska": "mkv"
    }

    mtype = mtype.split("/")[1]
    return mtype_special_cases.get(mtype.lower(), mtype).lower()


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

    # Get media type
    mtype = magic.from_file(image_path, mime=True)
    media_type = None
    media_format = "UNKNOWN"
    if mtype:
        if mtype.split("/")[0].lower() == "image":
            media_type = "image"
        elif mtype.split("/")[0].lower() == "video":
            media_type = "video"

        # Special case
        media_format = translate_mimetype_to_ext(mtype).upper()

    image_stats = {
        "id": image.id,
        "name": image.filename,
        "date": i_mtime,
        "media_type": media_type,
        "mimetype": media_format
    }

    return image_stats


def search_tags(keyword: str) -> List[tuple[Tag, int]]:
    '''Returns a list of matching tags from querying the keyword.'''
    # TODO: Add image count for each tag result
    matching_tags = Tag.query.filter(Tag.name.like(f"%{keyword}%")).all() or list()


    return [(tag, len(tag.images)) for tag in matching_tags]


def search_exact_tag(keyword: str) -> Tag:
    '''Returns an exact match for a Tag or none.'''
    # TODO: Add image count for each tag result
    return Tag.query.filter_by(name=keyword).first_or_404()


def is_image_file(file):
    """
    Returns True if file is an image.

    This relies on the accuracy of python magic.
    """
    file.seek(0)    # Reset seek header
    mime_type = magic.from_buffer(file.read(2048), mime=True)
    file.seek(0)    # Reset seek header again

    return mime_type.startswith("image/"), mime_type


def is_video_file(file):
    """
    Returns True if file is an video.

    This relies on the accuracy of python magic.
    """
    file.seek(0)    # Reset seek header
    mime_type = magic.from_buffer(file.read(2048), mime=True)
    file.seek(0)    # Reset seek header again

    return mime_type.startswith("video/"), mime_type


def get_thumbnail_dir(filename: str) -> str:
    """
    This function assumes that filename is only the filename
    and not the full filepath.
    """
    return os.path.normpath(os.path.join(
        app.config["THUMBNAIL_FOLDER"],
        f"{filename[:2]}/{filename[2:4]}"
    ))


def get_thumbnail_filepath(image_filename: str) -> str:
    """
    This function assumes that image_filename is only the filename
    and not the full filepath.
    """
    return os.path.normpath(os.path.join(
        get_thumbnail_dir(image_filename),
        f"sample_{os.path.splitext(image_filename)[0]}.jpg"
    ))


def create_thumbnail(input_path: str, video: bool, max_size = (650, 650)):
    thumbnail_path = get_thumbnail_filepath(os.path.basename(input_path))

    # Ensure thumbnail directory exists
    os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)

    if video is True:
        create_thumbnail_from_video(input_path, thumbnail_path)
    else:
        with PILImage.open(input_path) as img:
            img.thumbnail(max_size)
            img.convert("RGB").save(thumbnail_path)


def create_thumbnail_from_video(input_path: str, output_path: str):
    cap = cv2.VideoCapture(input_path)

    try:
        # Get the video duration in ms
        total_duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS) * 1000
        
        # Pick a time to extract a frame from the video
        time = total_duration / 4   # 1/4 into the video

        # Set the position of the frame to capture (in ms)
        cap.set(cv2.CAP_PROP_POS_MSEC, time)

        success, frame = cap.read()

        assert success is True

        cv2.imwrite(output_path, frame)
    finally:
        # Release the video capture
        cap.release()
