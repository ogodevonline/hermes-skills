"""Hermes constants stub for google-workspace skill"""
import os
from pathlib import Path

def get_hermes_home():
    return Path(os.path.expanduser("~/.hermes"))

def display_hermes_home():
    return "~/.hermes"