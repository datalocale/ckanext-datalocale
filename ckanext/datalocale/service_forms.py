import os, logging
from ckan.authz import Authorizer
from ckan.logic import check_access
import ckan.logic.action.create as create
import ckan.logic.action.update as update
import ckan.logic.action.get as get
from ckan.logic.converters import date_to_db, date_to_form, convert_to_extras, convert_from_extras
from ckan.logic import NotFound, NotAuthorized, ValidationError
from ckan.logic import tuplize_dict, clean_dict, parse_params
import ckan.logic.schema as default_schema
from ckan.logic.schema import group_form_schema
from ckan.logic.schema import package_form_schema
import ckan.logic.validators as val
from ckan.lib.base import BaseController, render, c, model, abort, request
from ckan.lib.base import redirect, _, config, h
from ckan.lib.package_saver import PackageSaver
from ckan.lib.field_types import DateType, DateConvertError
from ckan.lib.navl.dictization_functions import Invalid
from ckan.lib.navl.dictization_functions import validate, missing
from ckan.lib.navl.dictization_functions import DataError, flatten_dict, unflatten
from ckan.plugins import IDatasetForm, IGroupForm, IConfigurer, IGenshiStreamFilter, IRoutes
from ckan.plugins import implements, SingletonPlugin
from ckan.logic import check_access

from ckan.lib.navl.validators import (ignore_missing,
                                      not_empty,
                                      empty,
                                      ignore,
                                      keep_extras,
                                     )

log = logging.getLogger(__name__)

class DatalocaleServiceForm(SingletonPlugin):
    """
    This plugin implements an IGroupForm for form associated with a
    publisher group. ``IConfigurer`` is used to add the local template
    path and the IGroupForm supplies the custom form.
    """
    implements(IGroupForm, inherit=True)
    implements(IConfigurer, inherit=True)
    implements(IGenshiStreamFilter, inherit=True)
    implements(IRoutes)

    def update_config(self, config):
        """
        This IConfigurer implementation causes CKAN to look in the
        ```templates``` directory when looking for the group_form()
        """
        here = os.path.dirname(__file__)
        rootdir = os.path.dirname(os.path.dirname(here))
        template_dir = os.path.join(rootdir, 'ckanext',
                                    'datalocale', 'templates')
        config['extra_template_paths'] = ','.join([template_dir,
                config.get('extra_template_paths', '')])

        # Override /group/* as the default groups urls
        #config['ckan.default.group_type'] = 'service'

    def before_map(self, map):
        controller = 'ckanext.organizations.controllers:OrganizationController'
        map.connect('/service/users/{id}', controller=controller, action='users')
        return map

    def after_map(self, map):
        return map

    def new_template(self):
        """
        Returns a string representing the location of the template to be
        rendered for the new page
        """
        return 'forms/services/service_new.html'

    def index_template(self):
        """
        Returns a string representing the location of the template to be
        rendered for the index page
        """
        return 'forms/services/service_index.html'


    def read_template(self):
        """
        Returns a string representing the location of the template to be
        rendered for the read page
        """
        return 'forms/services/service_read.html'

    def history_template(self):
        """
        Returns a string representing the location of the template to be
        rendered for the read page
        """
        return 'forms/services/service_history.html'


    def group_form(self):
        """
        Returns a string representing the location of the template to be
        rendered.  e.g. "forms/group_form.html".
        """
        return 'forms/services/service_form.html'

    def group_types(self):
        """
        Returns an iterable of group type strings.

        If a request involving a group of one of those types is made, then
        this plugin instance will be delegated to.

        There must only be one plugin registered to each group type.  Any
        attempts to register more than one plugin instance to a given group
        type will raise an exception at startup.
        """
        return ["service"]

    def is_fallback(self):
        """
        Returns true iff this provides the fallback behaviour, when no other
        plugin instance matches a group's type.

        As this is not the fallback controller we should return False.  If
        we were wanting to act as the fallback, we'd return True
        """
        return False

    def form_to_db_schema(self):
        """
        Returns the schema for mapping group data from a form to a format
        suitable for the database.
        """
	schema = group_form_schema()
	schema.update({
		'foaf:name': [unicode, convert_to_extras, ignore_missing],
    	})
        return schema

    def db_to_form_schema(self):
        """
        Returns the schema for mapping group data from the database into a
        format suitable for the form (optional)
        """
	schema = group_form_schema()
	schema.update({
		'foaf:name': [convert_from_extras, ignore_missing],
    	})
	return schema

    def check_data_dict(self, data_dict):
        """
        Check if the return data is correct.

        raise a DataError if not.
        """

    def setup_template_variables(self, context, data_dict):
        """
        Add variables to c just prior to the template being rendered. We should
        use the available groups for the current user, but should be optional
        in case this is a top level group
        """
        c.user_groups = c.userobj.get_groups('service')
        local_ctx = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}

        try:
            check_access('group_create', local_ctx)
            c.is_superuser_or_groupadmin = True
        except NotAuthorized:
            c.is_superuser_or_groupadmin = False

        if 'group' in context:
            group = context['group']
            # Only show possible groups where the current user is a member
            c.possible_parents = c.userobj.get_groups('organization', 'admin')

            c.parent = None
            grps = group.get_groups('service')
            if grps:
                c.parent = grps[0]
            c.users = group.members_of_type(model.User)

    def filter(self, stream):
        ''' Add vocab tags to the bottom of the sidebar.'''
        from pylons import request
        from genshi.filters import Transformer
        from genshi.input import HTML
        routes = request.environ.get('pylons.routes_dict')
        if routes.get('controller') == 'group' \
            and routes.get('action') == 'index':
		html = '<li class="ckan-logged-in " style=""> <a class="" href="service/new"><img class="inline-icon " height="16px" width="16px" alt="None" src="/images/icons/group_add.png">Add an service</a></li>'
		'''h.check_access('group_update',{'id':c.userobj.get_groups(capacity='editor')})'''
		'''if(h.check_access('group_update',{'id':model.Group.id})) : '''
		route = h.subnav_named_route(c, h.icon('group_add') + _('Ajouter un service'), "service_new", action='new')
		route_loggedout = h.subnav_named_route(c, h.icon('group_add') + _('Se connecter pour ajouter un service'), "service_new", action='new')
		html = '<li style="display:none;" class="ckan-logged-in" > %s </li><li class="ckan-logged-out">%s</li>' % (route, route_loggedout)
		stream = stream | Transformer(
                        "//div[@id='minornavigation']//ul[@class='nav nav-pills']"
                    ).append(HTML(html))
        if routes.get('controller') == 'group' \
            and routes.get('action') == 'edit':
		html = ''
		stream = stream | Transformer(
                        "//div[@id='minornavigation']//li[@class='dropdown ']"
                    ).remove()
        return stream

