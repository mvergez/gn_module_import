import json
from pathlib import Path
from datetime import datetime

import pytest
from flask import testing, url_for
from werkzeug.datastructures import Headers
from werkzeug.exceptions import Unauthorized, Forbidden

from geonature import create_app
from geonature.utils.env import DB as db

from gn_module_import.db.models import TDatasets, TImports
from gn_module_import.steps import Step
from gn_module_import.utils.imports import get_table_class, get_import_table_name, get_archive_table_name


tests_path = Path(__file__).parent


class JSONClient(testing.FlaskClient):
    def open(self, *args, **kwargs):
        headers = kwargs.pop('headers', Headers())
        if 'Accept' not in headers:
            headers.extend(Headers({
                'Accept': 'application/json, text/plain, */*',
            }))
        if 'Content-Type' not in headers:
            headers.extend(Headers({
                'Content-Type': 'application/json',
            }))
            if 'data' in kwargs:
                kwargs['data'] = json.dumps(kwargs['data'])
        kwargs['headers'] = headers
        return super().open(*args, **kwargs)


def login(client, username='admin', password='admin'):
    data = {
        "login": username,
        "password": password,
        "id_application": client.application.config["ID_APPLICATION_GEONATURE"],
    }
    response = client.post(url_for("auth.login"), json=data)
    assert response.status_code == 200


class TestImports:
    @pytest.fixture(scope='session')
    def client(self):
        app = create_app()
        app.testing = True
        app.test_client_class = JSONClient

        # automatically begin a nested transaction after each commit
        # in order to rollback all changes at the end of tests
        @db.event.listens_for(db.session, "after_transaction_end")
        def restart_savepoint(session, transaction):
            if transaction.nested and not transaction._parent.nested:
                session.begin_nested()

        with app.app_context():
            db.session.begin_nested()  # execute tests in a savepoint
            with app.test_client() as client:
                yield client
            db.session.rollback()

    def test_list_imports(self, client):
        r = client.get('/import/imports/')  # TODO url_for
        assert r.status_code == Unauthorized.code
        login(client)
        r = client.get(url_for('import.get_import_list'))
        assert r.status_code == 200
        json_data = r.get_json()


    def test_import_process(self, client):
        login(client)

        # Upload step
        dataset = TDatasets.query.first()
        test_file = 'many_lines.csv'
        test_file_line_count = 100000
        with open(tests_path / 'files' / 'many_lines.csv', 'rb') as f:
            data = {
                'file': f,
                'datasetId': dataset.id_dataset,
            }
            r = client.post(url_for('import.upload_file'), data=data,
                            headers=Headers({'Content-Type': 'multipart/form-data'}))
        assert(r.status_code == 200)
        imprt_json = r.get_json()
        import_id = imprt_json['id_import']
        assert(imprt_json['author'])
        assert(imprt_json['date_create_import'])
        assert(imprt_json['date_update_import'])
        #assert(imprt_json['detected_encoding'] == 'utf-8')  # FIXME
        #assert(imprt_json['detected_format'] == 'csv')  # FIXME
        #assert(imprt_json['full_file_name'] == 'many_lines.csv')  # FIXME
        assert(imprt_json['id_dataset'] == dataset.id_dataset)
        assert(imprt_json['step'] == Step.Decode)

        # Decode step
        data = {
            'encoding': 'utf-8',
            'format': 'csv',
            'srid': 2154,
        }
        r = client.post(url_for('import.decode_file', import_id=import_id), data=data)
        assert(r.status_code == 200)
        imprt_json = r.get_json()
        assert(imprt_json['date_update_import'])
        assert(imprt_json['encoding'] == 'utf-8')
        assert(imprt_json['format_source_file'] == 'csv')
        assert(imprt_json['srid'] == 2154)
        assert(imprt_json['source_count'] == test_file_line_count)
        assert(imprt_json['step'] == Step.FieldMapping)
        assert(imprt_json['import_table'])
        imprt = TImports.query.get(import_id)
        ImportEntry = get_table_class(get_import_table_name(imprt))
        assert(db.session.query(ImportEntry).count() == imprt_json['source_count'])
        ImportArchiveEntry = get_table_class(get_archive_table_name(imprt))
        assert(db.session.query(ImportArchiveEntry).count() == imprt_json['source_count'])
