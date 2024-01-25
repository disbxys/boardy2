# Boardy2
Boardy2 uses PyQt to port a flask-based image gallery project to a desktop application.

If you are more comfortable running the project through a web browser, go to [here](#how-to-run) for instructions on doing so

## Dependencies
```
Python
Flask
Flask-SQLAlchemy
PyQt6
PyQt6-WebEngine
``````

## How to Run
This program can be run either through a web browser or as a desktop app by running ```main.py```.

To run through web browser, un-comment this line.
```python
app.run(host="0.0.0.0", port=PORT)
```
By default, the app will be available on the local network. To limit it to your pc, remove the host parameter so it would look like this:
```python
app.run(port=PORT)
```
<br>

To run through as a desktop app, un-comment this line.
```python
run_gui()
```

<i>P.S. You should make sure to comment out the other line (i.e. commenting out the second line if running through web browser or vice versa).</i>