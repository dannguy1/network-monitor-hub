# This blueprint is no longer used as credentials are managed alongside devices.
# Keeping the file for potential future use or different credential types.

from flask import Blueprint

bp = Blueprint('credentials', __name__)

# All credential routes (POST, GET, PUT, DELETE, /verify) have been removed. 