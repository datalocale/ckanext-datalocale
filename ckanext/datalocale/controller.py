from ckan.lib.base import BaseController
import ckan.plugins.toolkit as toolkit

class DocController(BaseController):
    def doc(self):
        return toolkit.render('doc.html')
