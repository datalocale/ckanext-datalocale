import os, logging
import ckan.logic as logic
from ckan.logic import NotFound, NotAuthorized, ValidationError
import ckan.logic.schema as default_schema
from ckan.lib.base import render, c, model, abort, request
from ckan.lib.base import redirect, _, config, h
from ckan.lib.navl.dictization_functions import Invalid, validate, missing
from ckan.plugins import IGroupForm, IConfigurer, IGenshiStreamFilter, IRoutes
from ckan.plugins import implements, SingletonPlugin
from ckan.logic import check_access
from pylons import request
from genshi.filters import Transformer
from genshi.input import HTML
from converters import convert_to_extras_groupform,  convert_from_extras_groupform
from ckan.logic.converters import date_to_db, date_to_form, convert_to_extras, convert_from_extras
from ckan.lib.navl.validators import (ignore_empty, ignore_missing,
                                      not_empty,
                                      empty,
                                      ignore,
                                      keep_extras,
                                     )

log = logging.getLogger(__name__)

class DatalocaleOrganizationForm(SingletonPlugin):
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
        config['ckan.default.group_type'] = 'organization'

    def before_map(self, map):
        controller = 'ckanext.datalocale.organization_controllers:DatalocaleOrganizationController'
        map.connect('/diffuseur/users/{id}', controller=controller,
                    action='users')
        map.connect('/diffuseur/apply/{id}', controller=controller,
                    action='apply')
        map.connect('/diffuseur/apply', controller=controller,
                    action='apply')
        map.connect('/diffuseur/edit/{id}', controller='group',
                    action='edit')
        map.connect('/diffuseur/new', controller=controller, action='new')
        map.connect('/diffuseur/{id}', controller=controller, action='read')
        map.connect('/diffuseur',  controller=controller, action='index')
        map.redirect('/diffuseur/publisher_read', '/diffuseur/organization_read')
        map.redirect('/organization', '/diffuseur')
        return map

    def after_map(self, map):
        return map

    def new_template(self):
        """
        Returns a string representing the location of the template to be
        rendered for the new page
        """
        return 'forms/organizations/organization_new.html'

    def index_template(self):
        """
        Returns a string representing the location of the template to be
        rendered for the index page
        """
        return 'forms/organizations/organization_index.html'


    def read_template(self):
        """
        Returns a string representing the location of the template to be
        rendered for the read page
        """
        return 'forms/organizations/organization_read.html'

    def history_template(self):
        """
        Returns a string representing the location of the template to be
        rendered for the read page
        """
        return 'forms/organizations/organization_history.html'


    def group_form(self):
        """
        Returns a string representing the location of the template to be
        rendered.  e.g. "forms/group_form.html".
        """
        return 'forms/organizations/organization_form.html'

    def group_types(self):
        """
        Returns an iterable of group type strings.

        If a request involving a group of one of those types is made, then
        this plugin instance will be delegated to.

        There must only be one plugin registered to each group type.  Any
        attempts to register more than one plugin instance to a given group
        type will raise an exception at startup.
        """
        return ["organization"]

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
        schema = default_schema.group_form_schema()
        schema.update({
		'foaf:name': [ignore_missing, convert_to_extras_groupform],
        'url': [ignore_missing, convert_to_extras_groupform],
        'mail': [ignore_missing, convert_to_extras_groupform],
        'phone': [ignore_missing, convert_to_extras_groupform],
        'street-address': [ignore_missing, convert_to_extras_groupform],
        'locality': [ignore_missing, convert_to_extras_groupform],
        'postal-code': [ignore_missing, convert_to_extras_groupform],
        'country-name': [ignore_missing, convert_to_extras_groupform],
    	})
        return schema

    def db_to_form_schema(self):
        """
        Returns the schema for mapping group data from the database into a
        format suitable for the form (optional)
        """
        schema = default_schema.group_form_schema()
        schema.update({
		'foaf:name': [convert_from_extras_groupform, ignore_missing],
        'url': [convert_from_extras_groupform, ignore_missing],
        'mail': [convert_from_extras_groupform, ignore_missing],
        'phone': [convert_from_extras_groupform, ignore_missing],
        'street-address': [convert_from_extras_groupform, ignore_missing],
        'locality': [convert_from_extras_groupform, ignore_missing],
        'postal-code': [convert_from_extras_groupform, ignore_missing],
        'country-name': [convert_from_extras_groupform, ignore_missing],
        'revision_id': [ignore_missing, unicode],
    	})
        return schema

    def check_data_dict(self, data_dict):
        """
        Check if the return data is correct.

        raise a DataError if not.
        """
    def db_to_form_schema_options(self, options):
        schema = self.db_to_form_schema()
        return schema
    
    def setup_template_variables(self, context, data_dict):
        """
        Add variables to c just prior to the template being rendered. We should
        use the available groups for the current user, but should be optional
        in case this is a top level group
        """
        import uuid
        c.key_upload = config.get('ckan.storage.key_prefix', 'file/') + request.params.get('filepath', str(uuid.uuid4()))
        
        c.user_groups = c.userobj.get_groups('service')
        local_ctx = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}
        if c.group:
            data_dict = {'id': c.group.id}
            c.group_dict = logic.get_action('group_show')(context, data_dict)
        else :
            c.group_dict = None

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
            grps = group.get_groups('organization')
            if grps:
                c.parent = grps[0]
            c.users = group.members_of_type(model.User)
            c.children_organization = group.get_children_groups('organization')
            c.children_services = group.get_children_groups('service')

        # find extras that are not part of our schema
        c.additional_extras = []
        schema_keys = self.form_to_db_schema().keys()
        if c.group_dict:
            extras = c.group_dict.get('extras', [])
            for extra in extras:
                if not extra['key'] in schema_keys:
                    c.additional_extras.append(extra)

    def filter(self, stream):
        controller = "ckanext.datalocale.organization_controllers:DatalocaleOrganizationController"
        serviceController = "ckanext.datalocale.service_controllers:DatalocaleServiceController"
        routes = request.environ.get('pylons.routes_dict')
        #Add button to the navbar
        if routes.get('controller') == serviceController and routes.get('action') == 'listFromOrganization':
            ##route = h.subnav_named_route(c, h.icon('group_add') + _(u'Ajouter un service pour ce groupe'), serviceController, action='new')
            ##route_loggedout = h.subnav_named_route(c, h.icon('group_add') + _(u'Se connecter pour ajouter un service pour ce groupe'), "service_new", action='new')
            ##html = '<li style="display:none;" class="ckan-logged-in" > %s </li><li class="ckan-logged-out">%s</li>' % (route, route_loggedout)
            html = ''
            stream = stream | Transformer(
                        "//div[@id='minornavigation']//ul[@class='nav nav-pills']"
                    ).append(HTML(html))
           
           
                    
            if routes.get('controller') == 'group' \
            and ( routes.get('action') == 'edit' or routes.get('action') == 'authz'):
                html = ''
                stream = stream | Transformer(
                        "//div[@id='minornavigation']//li[@class='dropdown ']"
                    ).remove()
                    
        #Add group hierarchy in group view sidebar  
        if routes.get('controller') == controller and routes.get('action') == 'read':
                children_organizations = c.group.get_children_groups('organization')
                children_services = c.group.get_children_groups('service')
                parent_organizations = c.group.get_groups('organization')
                parent_services = c.group.get_groups('service')
                html = ""
                if children_organizations or children_services : 
                        html += u" <h3>Producteurs</h3><ul class='groups no-break'>"
                        for children in children_organizations:
                            html += "<li><a href='%s/fr/diffuseur/%s' class='label'>%s</a><li>" % (c.site_url, children.get('name',''), children.get('title',''))
                        for children in children_services:
                            html += "<li><a href='%s/fr/producteur/%s' class='label'>%s</a><li>" % (c.site_url, children.get('name',''), children.get('title',''))
                        html += " </ul>"
                    
                stream = stream | Transformer(
                        "//div[@id='sidebar']//li[@id='hierarchie']"
                    ).append(HTML(html))
        return stream



