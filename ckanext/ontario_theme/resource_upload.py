# encoding: utf-8
import ckan.logic as logic
import ckan.lib.navl.dictization_functions as df
missing = df.missing
from six.moves.urllib.parse import urlparse
from werkzeug.utils import secure_filename

from ckan.lib.uploader import ResourceUpload as DefaultResourceUpload
from ckan.lib.uploader import get_storage_path, _get_underlying_file
import json

import os
import cgi
import datetime
import logging
import magic
import mimetypes

from werkzeug.datastructures import FileStorage as FlaskFileStorage

import ckan.lib.munge as munge
import ckan.logic as logic
import ckan.plugins as plugins
from ckan.common import config

ALLOWED_UPLOAD_TYPES = (cgi.FieldStorage, FlaskFileStorage)
MB = 1 << 20

log = logging.getLogger(__name__)

_storage_path = None
_max_resource_size = None
_max_image_size = None


def accepted_resource_formats():
    '''Returns list of accepted file extensions.
    '''
    resource_formats = []
    resource_format_path = os.path.join(os.path.dirname(__file__),
                                        'accepted_resource_formats.json')
    with open(resource_format_path) as format_file:
        file_resource_formats = json.loads(format_file.read())

        for format_line in file_resource_formats:
            resource_formats.append(format_line[0])
    return resource_formats



def allowed_file(url, resource):
    ''' Validates url (filename). Returns url or raises Invalid exception.
    '''
    try:
        if url is missing or not url or url.startswith('http'):
            # If there is no url or if its a link, the resource should be removed.
            # Unlikely but possible to alter URL field and not "remove" the resource.
            # Altering an URL with http://filename.ext changes the uploaded filename, allowing someone to by-pass validation below.
            # full resource dict isn't available here, only the form dict values, so can't rely on other fields like `url_type`.
            resource['clear_upload'] = 'true'
            return url
        # Using urlparse to handle any query strings.
        filename = os.path.basename(urlparse(url).path)
        # Only accepting single extensions (e.g. no filename.tar.gz).
        # Otherwise I'd have to check the combinations but this isnt needed at
        # this time.
        if filename.count('.') != 1 or not filename.rsplit('.', 1)[1].upper() in accepted_resource_formats():
            raise logic.ValidationError({'Upload': ['Filetype not supported.']})
        return url
    except Exception as e:
        log.error("ERROR")
        log.error(e)
        raise logic.ValidationError({'Upload': ['Filetype not supported.']})


class ResourceUpload(DefaultResourceUpload):
    def __init__(self, resource):
        path = get_storage_path()
        config_mimetype_guess = config.get('ckan.mimetype_guess', 'file_ext')

        if not path:
            self.storage_path = None
            return
        self.storage_path = os.path.join(path, 'resources')
        try:
            os.makedirs(self.storage_path)
        except OSError as e:
            # errno 17 is file already exists
            if e.errno != 17:
                raise
        self.filename = None
        self.mimetype = None

        url = resource.get('url')

        url = allowed_file(url, resource)

        upload_field_storage = resource.pop('upload', None)
        self.clear = resource.pop('clear_upload', None)

        if url and config_mimetype_guess == 'file_ext':
            self.mimetype = mimetypes.guess_type(url)[0]

        if isinstance(upload_field_storage, ALLOWED_UPLOAD_TYPES):
            self.filesize = 0  # bytes

            self.filename = upload_field_storage.filename
            # MODIFICATION START
            self.filename = secure_filename(self.filename) # Overkill but I
            # trust werkzueg over ckan.
            # MODIFICATION END
            self.filename = munge.munge_filename(self.filename)
            resource['url'] = self.filename
            resource['url_type'] = 'upload'
            resource['last_modified'] = datetime.datetime.utcnow()
            self.upload_file = _get_underlying_file(upload_field_storage)
            self.upload_file.seek(0, os.SEEK_END)
            self.filesize = self.upload_file.tell()
            # go back to the beginning of the file buffer
            self.upload_file.seek(0, os.SEEK_SET)

            # check if the mimetype failed from guessing with the url
            if not self.mimetype and config_mimetype_guess == 'file_ext':
                self.mimetype = mimetypes.guess_type(self.filename)[0]

            if not self.mimetype and config_mimetype_guess == 'file_contents':
                try:
                    self.mimetype = magic.from_buffer(self.upload_file.read(),
                                                      mime=True)
                    self.upload_file.seek(0, os.SEEK_SET)
                except IOError as e:
                    # Not that important if call above fails
                    self.mimetype = None

        elif self.clear:
            resource['url_type'] = ''

