# encoding: utf-8
import ckan.logic as logic
from ckan.plugins.toolkit import Invalid
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
from zipfile import ZipFile
import io

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
    '''Returns list of accepted file extensions and a
    list of accepted mime types.
    '''
    resource_format_path = os.path.join(os.path.dirname(__file__),
                                        'accepted_resource_formats.json')
    resource_exts = []
    resource_types = []
    with open(resource_format_path) as format_file:
        file_resource_formats = json.loads(format_file.read())

        for format_line in file_resource_formats:
            resource_exts.append(format_line[0].upper())
            resource_types.append(format_line[2])
    return resource_exts, resource_types

def allowed_ext(filename):
    '''Returns boolean. Checks if the file extension is acceptable.
    '''
    resource_exts, resource_types = accepted_resource_formats()
    return filename.rsplit('.', 1)[1].upper() in resource_exts

def allowed_mimetype(magic_mimetype):
    '''Returns boolean. Checks if the magic mimetype is acceptable.
    '''
    resource_exts, resource_types = accepted_resource_formats()
    # HACK UNTIL UNIX FILE UPGRADED
    if magic_mimetype == 'application/csv':
        return True

    if magic_mimetype == 'text/xml':
        return True

    return magic_mimetype in resource_types

def alert_invalidfile(resource, this_filename):
    log.error('Upload: Invalid upload file format.{}'.format
        (this_filename))
    # remove file - by default a resource can be added without any
    # values
    resource['url'] = None
    resource['url_type'] = ''
    raise logic.ValidationError(
        {'upload':
        ['Invalid upload file format, file has been removed.']}
    )

class ResourceUpload(DefaultResourceUpload):
    def __init__(self, resource):
        def _check_file_mimetype(self):
            try:
                self.mimetype = magic.from_buffer(self.upload_file.read(),
                                                mime=True)
                self.upload_file.seek(0, os.SEEK_SET)

                # If zip file, check mimetypes of each file
                if 'zip' in self.mimetype:
                    _check_zip_mimetype(self)
                            
                if not allowed_mimetype(self.mimetype):
                    alert_invalidfile(resource, self.filename)
            except IOError as e:
                # Not that important if call above fails
                self.mimetype = None

        def _check_zip_mimetype(self):
            # Wrap zip object in a StringIO
            # see: /usr/lib/ckan/default/lib/python3.8/site-packages/messytables/ods.py
            fileobj = io.BytesIO(self.upload_file.read())

            with ZipFile(fileobj) as this_zip:
                zip_list = this_zip.namelist()
                # Skip directory names
                for zip_item in zip_list:
                    if not zip_item.endswith("/"):
                        with this_zip.open(zip_item) as each_file:
                            try:
                                each_mimetype = magic.from_buffer(each_file.read(),
                                                mime=True)
                                if not allowed_mimetype(each_mimetype):
                                    alert_invalidfile(resource, self.filename)
                            except:
                                alert_invalidfile(resource, self.filename)
                        
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
        upload_field_storage = resource.pop('upload', None)
        self.clear = resource.pop('clear_upload', None)

        if url and config_mimetype_guess == 'file_ext':
            self.mimetype = mimetypes.guess_type(url)[0]

        if bool(upload_field_storage) and \
                isinstance(upload_field_storage, ALLOWED_UPLOAD_TYPES):
            self.filesize = 0  # bytes
            self.filename = upload_field_storage.filename
            self.filename = secure_filename(self.filename) # werkzueg
            self.filename = munge.munge_filename(self.filename)
            resource['url'] = self.filename
            resource['url_type'] = 'upload'
            resource['last_modified'] = datetime.datetime.utcnow()
            self.upload_file = _get_underlying_file(upload_field_storage)
            self.upload_file.seek(0, os.SEEK_END)
            self.filesize = self.upload_file.tell()
            # go back to the beginning of the file buffer
            self.upload_file.seek(0, os.SEEK_SET)

            # Check extension against allowed list of extensions
            if  '.' in self.filename and not allowed_ext(self.filename):
                alert_invalidfile(resource, self.filename)

            # Determine mimetype with python-magic
            _check_file_mimetype(self)
                      
        elif self.clear:
            resource['url_type'] = ''

        if url and not (resource.get('url_type') == 'upload') and not resource.get('format'):
            resource['format'] = 'WEB'

        if not (resource.get('format') == 'GeoJSON'):
            resource['format'] = resource['format'].upper()