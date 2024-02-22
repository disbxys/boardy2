# Boardy2
Boardy2 is a flask-based image gallery app.

If you are more comfortable running the project through a desktop, go checkout [Boardy3](https://github.com/disbxys/boardy3) for more information.

## Dependencies
```
Python
python-magic
Flask
Flask-SQLAlchemy
``````

<italic>You might need to also install `python-magic-bin` if running on windows.</italic>

## How to Run
This program is run through a web browser by running `launch.py`.

By default, the app will only be available on the local machine. To host it on the local network, add the <code>host</code> paramter:
```python
app.run(host="0.0.0.0", port=PORT)
```
where `0.0.0.0` means that the app will be hosted on the local network.

## Supported Media Formats
Boardy2 supports most image formats. Please refer to [python-magic](#python-magic) for specifics.

### Python-Magic
As the app uses python-magic to determine image file formats and mimetypes, any failure to detect an image format will most likely be due to python-magic.

## Migrating to Boardy3
If you want switch to hosting your media on a native desktop app, you can migrate your data to [Boardy3](https://github.com/disbxys/boardy3).

First clone the repo and cd into the directory where the repo is located.
```
git clone https://github.com/disbxys/boardy3.git

cd boardy3
```
From there, copy the `instance` and `db` folders from the root directory in your `boardy2` folder and paste them in the root directory folder in your `boardy3` folder.

You should be able to see all of your images after you run `launch.py`.

## Q&A
Q: Can't you do it this way?\
A: I probably haven't done it that way either because it would take too much time to do or it would feel too wierd to implment.

Q: Thank you for creating this app.\
A: Not a question but thank you