import logging
import genshi
import datetime
from urllib import urlencode
from ckan.lib.base import BaseController, c, model, request, render, h, g
from ckan.lib.base import ValidationException, abort, gettext
from pylons.i18n import get_lang, _
from ckan.lib.alphabet_paginate import AlphaPage
from ckan.lib.dictization.model_dictize import package_dictize
import ckan.forms
import ckan.authz as authz
import ckan.lib.dictization.model_save as model_save
import ckan.lib.mailer as mailer
import ckan.lib.navl.dictization_functions as dict_func
import ckan.logic as logic
import ckan.logic.action as action
import ckan.logic.schema as schema
import ckan.model as model
import ckan.plugins as plugins

from ckan.logic import NotFound, NotAuthorized, ValidationError
from ckan.logic import check_access, get_action
from ckan.logic import tuplize_dict, clean_dict, parse_params
from ckan.lib.helpers import Page

from ckan.plugins import IGroupController, implements
from ckan.controllers.group import GroupController


import pylons.config as config
from ckan.lib.navl.validators import (ignore_missing,
                                      not_empty,
                                      empty,
                                      ignore,
                                      keep_extras,)

log = logging.getLogger(__name__)

'''
    Copy of the ckan/ckanext/organizations/controllers.py
    Main modification : path of template (render) 
'''
class DatalocaleOrganizationController(GroupController):
    implements(IGroupController, inherit=True)
       
    def index(self):
        group_type = self._guess_group_type()
        group_type = "organization"

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True,
                   'with_private': False}

        data_dict = {'all_fields': True, 'type': 'organization'}

        try:
            check_access('site_read', context)
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))

        results = get_action('group_list')(context, data_dict)
    
        new_results = []
        for res in results:
            if res["type"] == "organization":
                c.group = model.Group.get(res["name"])
                children = c.group.get_children_groups('service')
                res["children_num"]= len(children)
                #data_dict = {"group_name":res["name"], "with_services": True}
                #dataset_num = len(get_action('get_package_from_group')(context, data_dict))
                #res["dataset_num"] = dataset_num
                
                data_dict = {
                        'q': 'groups:' + res["name"],
                        'fq':'',
                        'facet.field':"['groups', 'tags', 'res_format', 'license']",
                        'extras':''
                        }
                query = get_action('package_search')(context,data_dict)
                res["dataset_num"] = query["count"]
                new_results.append(res)
        c.page = Page(
            collection=new_results,
            page=request.params.get('page', 1),
            url=h.pager_url,
            items_per_page=20
        )
        return render( self._index_template(group_type) )
    def read(self, id):
        from ckan.lib.search import SearchError
        group_type = self._get_group_type(id.split('@')[0])
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'schema': self._form_to_db_schema(group_type=group_type),
                   'for_view': True, 'extras_as_string': True}
        data_dict = {'id': id}
        q = c.q = request.params.get('q', '') # unicode format (decoded from utf8)

        try:
            c.group_dict = get_action('group_show')(context, data_dict)
            c.group = context['group']
        except NotFound:
            abort(404, _('Group not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read group %s') % id)

        # Search within group
        q += ' groups: "%s"' % c.group_dict.get('name')

        try:
            description_formatted = ckan.misc.MarkdownFormat().to_html(c.group_dict.get('description',''))
            c.description_formatted = genshi.HTML(description_formatted)
        except Exception, e:
            error_msg = "<span class='inline-warning'>%s</span>" % _("Cannot render description")
            c.description_formatted = genshi.HTML(error_msg)

        c.group_admins = self.authorizer.get_admins(c.group)

        context['return_query'] = True

        limit = 20
        try:
            page = int(request.params.get('page', 1))
        except ValueError, e:
            abort(400, ('"page" parameter must be an integer'))

        # most search operations should reset the page counter:
        params_nopage = [(k, v) for k,v in request.params.items() if k != 'page']

        def search_url(params):
            url = h.url_for(controller='group', action='read', id=c.group_dict.get('name'))
            params = [(k, v.encode('utf-8') if isinstance(v, basestring) else str(v)) \
                            for k, v in params]
            return url + u'?' + urlencode(params)

        def drill_down_url(**by):
            params = list(params_nopage)
            params.extend(by.items())
            return search_url(set(params))

        c.drill_down_url = drill_down_url

        def remove_field(key, value):
            params = list(params_nopage)
            params.remove((key, value))
            return search_url(params)

        c.remove_field = remove_field

        def pager_url(q=None, page=None):
            params = list(params_nopage)
            params.append(('page', page))
            return search_url(params)

        try:
            c.fields = []
            search_extras = {}
            for (param, value) in request.params.items():
                if not param in ['q', 'page'] \
                        and len(value) and not param.startswith('_'):
                    if not param.startswith('ext_'):
                        c.fields.append((param, value))
                        q += ' %s: "%s"' % (param, value)
                    else:
                        search_extras[param] = value


            fq = 'capacity:"public"'
            if (c.userobj and c.group and c.userobj.is_in_group(c.group)):
                fq = ''

        
            data_dict = {
                'q':q,
                'fq':fq,
                'facet.field':g.facets,
                'rows':limit,
                'start':(page-1)*limit,
                'extras':search_extras
            }

            query = get_action('package_search')(context,data_dict)

            c.page = h.Page(
                collection=query['results'],
                page=page,
                url=pager_url,
                item_count=query['count'],
                items_per_page=limit
            )
            c.facets = query['facets']
            c.search_facets = query['search_facets']
            c.page.items = query['results']
        except SearchError, se:
            log.error('Group search error: %r', se.args)
            c.query_error = True
            c.facets = {}
            c.page = h.Page(collection=[])

        # Add the group's activity stream (already rendered to HTML) to the
        # template context for the group/read.html template to retrieve later.
        c.group_activity_stream = \
                ckan.logic.action.get.group_activity_list_html(context,
                    {'id': c.group_dict['id']})

        return render( self._read_template(c.group_dict['type']) )
         
    def _send_application( self, group, reason  ):
        from genshi.template.text import NewTextTemplate

        if not reason:
            h.flash_error(_("There was a problem with your submission, \
                             please correct it and try again"))
            errors = {"reason": ["No reason was supplied"]}
            return self.apply(group.id, errors=errors,
                              error_summary=action.error_summary(errors))

        admins = group.members_of_type( model.User, 'admin' ).all()
        recipients = [(u.fullname,u.email) for u in admins] if admins else \
                     [(config.get('ckan.admin.name', "CKAN Administrator"),
                       config.get('ckan.admin.email', None), )]

        if not recipients:
            h.flash_error(_("There is a problem with the system configuration"))
            errors = {"reason": ["No group administrator exists"]}
            return self.apply(group.id, data=data, errors=errors,
                              error_summary=action.error_summary(errors))

        extra_vars = {
            'group'    : group,
            'requester': c.userobj,
            'reason'   : reason
        }
        email_msg = render("forms/organizations/email/join_publisher_request.txt", extra_vars=extra_vars,
                         loader_class=NewTextTemplate)

        try:
            for (name,recipient) in recipients:
                mailer.mail_recipient(name,
                               recipient,
                               "Publisher request",
                               email_msg)
                print('Mail send to %s (%s) Objet "Publisher request" : %s ' % (name,recipient, email_msg))
        except:
            h.flash_error(_("There is a problem with the system configuration"))
            errors = {"reason": ["No mail server was found"]}
            return self.apply(group.id, errors=errors,
                              error_summary=action.error_summary(errors))

        h.flash_success(_("Your application has been submitted"))
        h.redirect_to( 'organization_read', id=group.name)

    def apply(self, id=None, data=None, errors=None, error_summary=None):
        """
        A user has requested access to this publisher and so we will send an
        email to any admins within the publisher.
        """
        if 'parent' in request.params and not id:
            id = request.params['parent']

        if id:
            c.group = model.Group.get(id)
            if 'save' in request.params and not errors:
                return self._send_application(c.group, request.params.get('reason', None))

        self._add_publisher_list()
        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}

        data.update(request.params)

        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}
        c.form = render('forms/organizations/organization_apply_form.html', extra_vars=vars)
        return render('forms/organizations/organization_apply.html')

    def _add_users( self, group, parameters  ):
        if not group:
            h.flash_error(_("There was a problem with your submission, "
                             "please correct it and try again"))
            errors = {"reason": ["No reason was supplied"]}
            return self.apply(group.id, errors=errors,
                              error_summary=action.error_summary(errors))

        data_dict = logic.clean_dict(dict_func.unflatten(
                logic.tuplize_dict(logic.parse_params(request.params))))
        data_dict['id'] = group.id

        # Temporary fix for strange caching during dev
        l = data_dict['users']
        for d in l:
            d['capacity'] = d.get('capacity','editor')

        context = {
            "group" : group,
            "schema": schema.default_group_schema(),
            "model": model,
            "session": model.Session,
            'user': c.user or c.author
        }

        # Temporary cleanup of a capacity being sent without a name
        users = [d for d in data_dict['users'] if len(d) == 2]
        data_dict['users'] = users

        model.repo.new_revision()
        model_save.group_member_save(context, data_dict, 'users')
        model.Session.commit()
        for user in users:
            roles = []
            roles.append(user.get('capacity'))
            logic.get_action('user_role_update')(context, {'user': user.get('name',''), 'domain_object':group.id, 'roles': roles})   
        h.redirect_to( controller='group', action='edit', id=group.name)
   
    def new(self, data=None, errors=None, error_summary=None):
        group_type = "organization"
        if data:
            data['type'] = group_type

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'save': 'save' in request.params,
                   'parent': request.params.get('parent', None)}
        try:
            check_access('group_create',context)
        except NotAuthorized:
            abort(401, _('Unauthorized to create a group'))

        if context['save'] and not data:
            return self._save_new(context, group_type)

        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}

        self._setup_template_variables(context,data)
        c.form = render(self._group_form(group_type=group_type), extra_vars=vars)
        return render(self._new_template(group_type))

    def users(self, id, data=None, errors=None, error_summary=None):
        c.group = model.Group.get(id)

        if not c.group:
            abort(404, _('Group not found'))

        context = {
                   'model': model,
                   'session': model.Session,
                   'user': c.user or c.author,
                   'group': c.group }

        try:
            logic.check_access('group_update',context)
        except logic.NotAuthorized, e:
            abort(401, _('User %r not authorized to edit %s') % (c.user, id))

        if 'save' in request.params and not errors:
            return self._add_users(c.group, request.params)

        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}

        data['users'] = []
        data['users'].extend( { "name": user.name,
                                "capacity": "admin" }
                                for user in c.group.members_of_type( model.User, "admin"  ).all() )
        data['users'].extend( { "name": user.name,
                                "capacity": "editor" }
                                for user in c.group.members_of_type( model.User, 'editor' ).all() )

        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}
        c.form = render('forms/organizations/organization_users_form.html', extra_vars=vars)
        return render('forms/organizations/organization_users.html')

    def _add_publisher_list(self):
        c.possible_parents = model.Session.query(model.Group).filter(model.Group.state == 'active').order_by(model.Group.title).all()
    
