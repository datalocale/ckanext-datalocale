import os
import re
import urllib
import uuid
from datetime import datetime
from cgi import FieldStorage

from pylons import request, response
from pylons.controllers.util import abort, redirect_to
from pylons import config
from paste.fileapp import FileApp
from paste.deploy.converters import asbool

from ckan.lib.base import BaseController, c, request, render, config, h, abort
from ckan.lib.jsonp import jsonpify
import ckan.model as model
import ckan.authz as authz

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
try:
    import json
except:
    import simplejson as json

from logging import getLogger
log = getLogger(__name__)


BUCKET = config.get('ckan.storage.bucket', 'default')
key_prefix = config.get('ckan.storage.key_prefix', 'file/')
from ckan.controllers.storage import StorageController
from ckan.controllers.storage import get_ofs, authorize
    


class DatalocaleStorageController(BaseController):
    '''Upload to storage backend.
    '''
    _ofs_impl = None
    
    @property
    def ofs(self):
        if not DatalocaleStorageController._ofs_impl:
            DatalocaleStorageController._ofs_impl = get_ofs()
        return DatalocaleStorageController._ofs_impl

    def upload_handle(self):
        bucket_id = BUCKET
        params = dict(request.params.items())
        stream = params.get('file')
        label = params.get('key')
        label = label+'-'+stream.filename
        authorize('POST', BUCKET, label, c.userobj, self.ofs)
        if not label:
            abort(400, "No label")
        if not isinstance(stream, FieldStorage):
            abort(400, "No file stream.")
        del params['file']
        params['filename-original'] = stream.filename
        #params['_owner'] = c.userobj.name if c.userobj else ""
        params['uploaded-by'] = c.userobj.name if c.userobj else ""

        self.ofs.put_stream(bucket_id, label, stream.file, params)
        # Do not redirect here as it breaks js file uploads (get infinite loop
        # in FF and crash in Chrome)
        label = request.params.get('label', label)
        c.file_url = h.url_for('storage_file',
                               label=label,
                               qualified=True)
        return c.file_url

    