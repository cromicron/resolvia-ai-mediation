from flask import render_template
from . import main

@main.route('/')
def index():
    """main page route"""
    return render_template('main/index.html')
