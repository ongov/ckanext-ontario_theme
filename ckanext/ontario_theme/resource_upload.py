# encoding: utf-8
import ckan.logic as logic
from ckan.plugins.toolkit import Invalid

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
    '''Returns list of accepted formats compatible with formats returned from
    magic's mimetype that's returned.
    '''
    resource_formats = []
    resource_format_path = os.path.join(os.path.dirname(__file__),
                                        'accepted_resource_formats.json')
    log.error(resource_format_path)
    with open(resource_format_path) as format_file:
        file_resource_formats = json.loads(format_file.read())

        for format_line in file_resource_formats:
            resource_formats.append(format_line[2])
    log.error(resource_formats)
    return resource_formats


class ResourceUpload(DefaultResourceUpload):
    def __init__(self, resource):
        log.error("Debug 1 \n\n")
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

        if isinstance(upload_field_storage, ALLOWED_UPLOAD_TYPES):
            self.filesize = 0  # bytes

            self.filename = upload_field_storage.filename
            self.filename = munge.munge_filename(self.filename)
            resource['url'] = self.filename
            resource['url_type'] = 'upload'
            resource['last_modified'] = datetime.datetime.utcnow()
            self.upload_file = _get_underlying_file(upload_field_storage)
            self.upload_file.seek(0, os.SEEK_END)
            self.filesize = self.upload_file.tell()
            # go back to the beginning of the file buffer
            self.upload_file.seek(0, os.SEEK_SET)

            # MODIFICATION START
            # Note: If resubmitting a failed form without clearing the file
            # the ResourceUpload.upload function would be called skipping the
            # init call.
            #
            # check if the mimetype is allowed.
            temp_mimetype = magic.from_buffer(self.upload_file.read(),
                                              mime=True)
            if temp_mimetype not in accepted_resource_formats():
                log.error('Upload: Invalid upload file format. {}'
                          .format(temp_mimetype))
                # remove file
                # Note: by default a resource can be added with no values for
                # any field.
                upload_field_storage = None
                self.filename = None
                resource['url'] = None
                resource['url_type'] = ''
                # raise validation error
                raise logic.ValidationError(
                    {'upload':
                     ['Invalid upload file format, file has been removed.']}
                )

            # MODIFICATION END

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
