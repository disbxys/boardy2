# Boardy2
Boardy2 uses PyQt to port a flask-based image gallery project to a desktop application.

If you are more comfortable running the project through a web browser, go to [here](#how-to-run) for instructions on doing so

## Dependencies
```
Python
python-magic
Flask
Flask-SQLAlchemy
PyQt6
PyQt6-WebEngine
``````

<italic>You might need to also install ```python-magic-bin``` if running on windows.</italic>

## How to Run
This program can be run either through a web browser or as a desktop app by running ```main.py```.

### Web Browser
To run through web browser, un-comment this line.
```python
app.run(port=PORT)
```
By default, the app will only be available on the local machine. To host it on the local network, add the <code>host</code> paramter:
```python
app.run(host="0.0.0.0", port=PORT)
```
where <code>"0.0.0.0"</code> means that the app will be hosted on the local network.

### Desktop App
To run through as a desktop app, un-comment this line.
```python
run_gui()
```

<i>P.S. You should make sure to comment out the other line (i.e. commenting out the second line if running through web browser or vice versa).</i>

## Supported Media Formats
Boardy2 supports most image formats. Please refer to [python-magic](#python-magic) for specifics.

### Python-Magic
As the app uses python-magic to determine image file formats and mimetypes, any failure to detect an image format will most likely be due to python-magic.

## Q&A
Q: Can't you do it this way?\
A: I probably haven't done it that way either because it would take too much time to do or it would feel too wierd to implment.

Q: Thank you for creating this app.\
A: Not a question but thank you