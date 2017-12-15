from __future__ import print_function

import sys
import itertools
import ckan.lib.cli
import ckan.logic as logic
import ckan.model as model


class DataStoreCleanup(ckan.lib.cli.CkanCommand):
    """Clean the datastore db from non-existent resources tables"""
    # Copied from ckanext-switzerland at f00d848f022a9080f4aef36ed305fa73292fdb28
    summary = __doc__

    def __init__(self, name):
        super(DataStoreCleanup, self).__init__(name)
        self.parser.add_option(
            '-n', '--dry-run', dest='dry_run',
            action='store_true', default=False,
            help='do not perform actions, print what would happen',
        )

    def command(self):
        # load pylons config
        self._load_config()
        user = logic.get_action('get_site_user')({'ignore_auth': True}, {})
        context = {
            'model': model,
            'session': model.Session,
            'user': user['name']
        }
        try:
            logic.check_access('datastore_delete', context)
            logic.check_access('resource_show', context)
        except logic.NotAuthorized:
            print("User {} is not authorized to perform this action.".format(user['name']))
            sys.exit(1)

        dry_run = self.options.dry_run

        # query datastore to get all resources from the _table_metadata
        resource_id_list = []
        for offset in itertools.count(start=0, step=100):
            print("Load metadata records from datastore (offset: %s)" % offset)
            record_list, has_next_page = self._get_datastore_table_page(context, offset)  # noqa
            resource_id_list.extend(record_list)
            if not has_next_page:
                break

        # delete the rows of the orphaned datastore tables
        delete_count = 0
        for resource_id in resource_id_list:
            msg = "Table '%s' deleted (not dropped)" % resource_id
            if not dry_run:
                logic.get_action('datastore_delete')(
                    context,
                    {'resource_id': resource_id, 'force': True}
                )
                print(msg)
            else:
                print(msg + ' [DRY RUN]')
            delete_count += 1

        print("Deleted content of %s tables" % delete_count)

    def _get_datastore_table_page(self, context, offset=0):
        # query datastore to get all resources from the _table_metadata
        result = logic.get_action('datastore_search')(
            context,
            {
                'resource_id': '_table_metadata',
                'offset': offset
            }
        )

        resource_id_list = []
        for record in result['records']:
            # ignore 'alias' records
            if record.get('alias_of'):
                continue
            try:
                logic.get_action('resource_show')(
                    context,
                    {'id': record['name']}
                )
                print("Resource '%s' found" % record['name'])
            except logic.NotFound:
                resource_id_list.append(record['name'])
                print("Resource '%s' *not* found" % record['name'])

        # are there more records?
        has_next_page = (len(result['records']) > 0)

        return resource_id_list, has_next_page
