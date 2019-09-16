from flask import (
    Blueprint,
    current_app,
    request,
    jsonify
)

from werkzeug.utils import secure_filename

import os

import pathlib

import pandas as pd

import numpy as np

import threading

import datetime

import sqlalchemy
from sqlalchemy import func, text, select, update, event
from sqlalchemy.sql.elements import quoted_name
from sqlalchemy.sql import column

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import QuotedString, AsIs, quote_ident
from psycopg2.extras import execute_values

from geonature.utils.utilssqlalchemy import json_resp
from geonature.utils.env import DB
from geonature.core.gn_meta.models import TDatasets
from geonature.core.gn_synthese.models import (
    Synthese,
    TSources,
    CorObserverSynthese
)
from geonature.core.gn_commons.models import BibTablesLocation
from geonature.utils.env import DB
from geonature.core.gn_permissions import decorators as permissions

from pypnnomenclature.models import TNomenclatures

from .db.models import (
    TImports,
    CorRoleImport,
    CorImportArchives,
    generate_user_table_class
)

from .db.query import (
    get_table_info,
    get_table_list,
    test_user_dataset,
    delete_import_CorImportArchives,
    delete_import_CorRoleImport,
    delete_import_TImports,
    delete_tables,
    get_table_names,
    check_sql_words,
    get_full_table_name,
    set_imports_table_name,
    get_synthese_info,
    load_csv_to_db,
    get_row_number
)

from .utils.clean_names import*
from .upload.upload_process import upload
from .upload.upload_errors import*
from .goodtables_checks.check_user_file import check_user_file
from .transform.transform import data_cleaning
from .logs import logger
from .api_error import GeonatureImportApiError
from .extract.extract import extract
from .load.load import load
from .wrappers import checker
from .load.utils import compute_df

import pdb

blueprint = Blueprint('import', __name__)


@blueprint.errorhandler(GeonatureImportApiError)
def handle_geonature_import_api(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@blueprint.route('', methods=['GET'])
@permissions.check_cruved_scope('R', True, module_code="IMPORT")
@json_resp
def get_import_list(info_role):
    """
        return import list
    """
    try:
        results = DB.session.query(TImports)\
                    .order_by(TImports.id_import)\
                    .filter(TImports.step >= 2)
        nrows = DB.session.query(TImports).count()
        history = []
        if not results or nrows == 0:
            return {
                "empty": True
            }, 200
        for r in results:
            if r.date_end_import is None:
                date_end_import = 'En cours'
            else:
                date_end_import = r.date_end_import
            prop = {
                "id_import": r.id_import,
                "format_source_file": r.format_source_file,
                "srid": r.srid,
                "import_table": r.import_table,
                "id_dataset": r.id_dataset,
                "id_mapping": r.id_mapping,
                "date_create_import": str(r.date_create_import),#recupérer seulement date et pas heure
                "date_update_import": str(r.date_update_import),#recupérer seulement date et pas heure
                "date_end_import": str(date_end_import),
                "source_count": r.source_count,
                "import_count": r.import_count,
                "taxa_count": r.taxa_count,
                "date_min_data": str(r.date_min_data),
                "date_max_data": str(r.date_max_data),
                "step": r.step,
                "dataset_name": DB.session\
                    .query(TDatasets.dataset_name)\
                    .filter(TDatasets.id_dataset == r.id_dataset)\
                    .one()[0]
            }
            history.append(prop)
        return {
                   "empty": False,
                   "history": history,
               }, 200
    except Exception:
        return 'INTERNAL SERVER ERROR ("get_import_list() error"): contactez l\'administrateur du site', 500


@blueprint.route('/delete_step1', methods=['GET'])
@permissions.check_cruved_scope('R', True, module_code="IMPORT")
@json_resp
def delete_step1(info_role):
    """
        delete id_import previously created by current id_role having step = 1 value
        (might happen when user uploads several files during the same import process (=same id_import)
        and finally interrupts the process without any valid import)
    """
    try:
        list_to_delete = DB.session.query(TImports.id_import)\
            .filter(CorRoleImport.id_import == TImports.id_import)\
            .filter(CorRoleImport.id_role == info_role.id_role)\
            .filter(TImports.step == 1)\

        ids = []

        for id in list_to_delete:
            delete_import_CorImportArchives(id.id_import)
            delete_import_CorRoleImport(id.id_import)
            delete_import_TImports(id.id_import)
            ids.append(id.id_import)
            DB.session.commit()

        return {"deleted_step1_imports":ids},200

    except Exception:
        return 'INTERNAL SERVER ERROR ("delete_step1() error"): contactez l\'administrateur du site', 500


@blueprint.route('/datasets', methods=['GET'])
@permissions.check_cruved_scope('C', True, module_code="IMPORT")
@json_resp
def get_user_datasets(info_role):
    """
        load user datasets
    """

    try:
        results = DB.session.query(TDatasets).\
            filter(TDatasets.id_dataset == Synthese.id_dataset).\
            filter(CorObserverSynthese.id_synthese == Synthese.id_synthese).\
            filter(CorObserverSynthese.id_role == info_role.id_role).all()

        if results:
            datasets = []
            for row in results:
                d = {'datasetId': row.id_dataset,\
                     'datasetName': row.dataset_name}
                datasets.append(d)
            return datasets,200
        else:
            return 'Attention, vous n\'avez aucun jeu de données déclaré', 400
    except Exception:
        return 'INTERNAL SERVER ERROR ("get_user_datasets() error"): contactez l\'administrateur du site', 500


@blueprint.route('/cancel_import/<import_id>', methods=['GET'])
@permissions.check_cruved_scope('C', True, module_code="IMPORT")
@json_resp
def cancel_import(info_role, import_id):
    try:
        
        if import_id == "undefined":
            server_response = {'deleted_id_import': "canceled"}
            return server_response,200
        

        # get step number
        step = DB.session.query(TImports.step)\
            .filter(TImports.id_import == import_id)\
            .one()[0]

        if step > 1:

            # get data table name
            user_data_name = DB.session.query(TImports.import_table)\
                .filter(TImports.id_import == import_id)\
                .one()[0]

            # set data table names
            archives_full_name = get_full_table_name(blueprint.config['ARCHIVES_SCHEMA_NAME'],user_data_name)
            imports_table_name = set_imports_table_name(user_data_name)
            imports_full_name = get_full_table_name('gn_imports', imports_table_name)

            # delete tables
            engine = DB.engine
            is_gn_imports_table_exist = engine.has_table(imports_table_name, schema=blueprint.config['IMPORTS_SCHEMA_NAME'])
            if is_gn_imports_table_exist:
                DB.session.execute("DROP TABLE {}".format(imports_full_name))

            DB.session.execute("DROP TABLE {}".format(archives_full_name))

        # delete metadata
        DB.session.query(TImports).filter(TImports.id_import == import_id).delete()
        DB.session.query(CorRoleImport).filter(CorRoleImport.id_import == import_id).delete()
        DB.session.query(CorImportArchives).filter(CorImportArchives.id_import == import_id).delete()
        
        DB.session.commit()
        DB.session.close()
        server_response = {'deleted_id_import': import_id}

        return server_response, 200
    except Exception:
        raise
        return 'INTERNAL SERVER ERROR ("delete_TImportRow() error"): contactez l\'administrateur du site', 500


@blueprint.route('/uploads', methods=['GET', 'POST'])
@permissions.check_cruved_scope('C', True, module_code="IMPORT")
@json_resp
@checker('Total time to post user file and fill metadata')
def post_user_file(info_role):
    """
        - load user file in "upload" directory
        - check user file data with goodtables library (column names, row duplicates, ...)
        - copy user file raw data in 2 geonature db tables (in archives and imports schemas)
        - fill t_imports, cor_role_import, cor_archive_import
        - return id_import and column names list
        - delete user file in upload directory

        # Note perso:
        # prevoir un boolean (ou autre) pour bloquer la possibilité de l'utilisateur de lancer plusieurs uploads sans passer par interface front

    """

    try:

        logger.info('*** START UPLOAD USER FILE')

        ### INITIALIZE VARIABLES

        is_file_saved = False
        is_id_import = False
        errors = []

        MAX_FILE_SIZE = blueprint.config['MAX_FILE_SIZE']
        ALLOWED_EXTENSIONS = blueprint.config['ALLOWED_EXTENSIONS']
        DIRECTORY_NAME = blueprint.config["UPLOAD_DIRECTORY"]
        MODULE_URL = blueprint.config["MODULE_URL"]
        PREFIX = blueprint.config['PREFIX']
        ARCHIVES_SCHEMA_NAME = blueprint.config['ARCHIVES_SCHEMA_NAME']
        IMPORTS_SCHEMA_NAME = blueprint.config['IMPORTS_SCHEMA_NAME']
        N_MAX_ROWS_CHECK = 100000000

        
        ### SAVES USER FILE IN UPLOAD DIRECTORY
        
        logger.info('* START SAVE USER FILE IN UPLOAD DIRECTORY')

        uploaded_file = upload(request, MAX_FILE_SIZE, ALLOWED_EXTENSIONS, DIRECTORY_NAME, MODULE_URL)

        # checks if error in user file or user http request:
        if uploaded_file['error'] == 'no_file':
            errors.append(no_file)
        if uploaded_file['error'] == 'empty':
            errors.append(empty)
        if uploaded_file['error'] == 'bad_extension':
            errors.append(extension_error)
        if uploaded_file['error'] == 'long_name':
            errors.append(long_name)
        if uploaded_file['error'] == 'max_size':
            errors.append(max_size)  
        if uploaded_file['error'] == 'unknown':
            errors.append(unkown)        
        
        if uploaded_file['error'] != '':
            logger.error('Saving user file : %s', errors)
            return errors,400

        full_path = uploaded_file['full_path']

        is_file_saved = uploaded_file['is_uploaded']

        logger.info('* END SAVE USER FILE IN UPLOAD DIRECTORY')


        ### CHECKS USER FILE

        logger.info('* START CHECK USER FILE VALIDITY')

        report = check_user_file(full_path, N_MAX_ROWS_CHECK)

        # reports user file errors:
        if len(report['errors']) > 0:
            logger.error(report['errors'])
            return report['errors'],400

        logger.info('* END CHECK USER FILE VALIDITY')


        ### CREATES CURRENT IMPORT IN TIMPORTS (SET STEP TO 1 AND DATE/TIME TO CURRENT DATE/TIME)
        
        # get form data
        metadata = request.form.to_dict()

        # Check if id_dataset value is allowed (prevent from forbidden manual change in url (url/process/N))
        is_dataset_allowed = test_user_dataset(info_role.id_role, metadata['datasetId'])
        if not is_dataset_allowed:
            logger.error('Provided dataset is not allowed')
            return \
            'L\'utilisateur {} n\'est pas autorisé à importer des données vers l\'id_dataset {}'\
            .format(info_role.id_role, int(metadata['datasetId']))\
            ,403

        # start t_imports filling and fill cor_role_import
        if metadata['importId'] == 'undefined':
            # if first file uploaded by the user in the current import process :
            init_date = datetime.datetime.now()
            insert_t_imports = TImports(
                date_create_import = init_date,
                date_update_import = init_date,
            )
            DB.session.add(insert_t_imports)
            DB.session.flush()
            id_import = insert_t_imports.id_import
            logger.debug('id_import = %s', id_import)
            logger.debug('id_role = %s', info_role.id_role)
            # fill cor_role_import
            insert_cor_role_import = CorRoleImport(id_role=info_role.id_role, id_import=id_import)
            DB.session.add(insert_cor_role_import)
            DB.session.flush()
        else:
            # if other file(s) already uploaded by the user in the current import process :
            id_import = int(metadata['importId'])
            DB.session.query(TImports)\
                .filter(TImports.id_import == id_import)\
                .update({
                    TImports.date_update_import:datetime.datetime.now()
                    })

        if isinstance(id_import, int):
            is_id_import = True

        # set step to 1 in t_imports table
        DB.session.query(TImports)\
            .filter(TImports.id_import == id_import)\
            .update({
                TImports.step:1
                })

        
        # GET/SET FILE,SCHEMA,TABLE,COLUMN NAMES

        # file name treatment
        file_name_cleaner = clean_file_name(uploaded_file['file_name'], uploaded_file['extension'], id_import)
        if len(file_name_cleaner['errors']) > 0:
            # if user file name is not valid, an error is returned
            return file_name_cleaner['errors'],400

        ## get/set table and column names
        separator = metadata['separator']
        table_names = get_table_names(ARCHIVES_SCHEMA_NAME, IMPORTS_SCHEMA_NAME, file_name_cleaner['clean_name'])
        logger.debug('full DB user table name = %s', table_names['imports_full_table_name'])

        # pk name to include (because copy_from method requires a primary_key)
        pk_name = "".join([PREFIX, 'pk'])

        # clean column names
        columns = [clean_string(x) for x in report['column_names']]


        """
        CREATES TABLES CONTAINING RAW USER DATA IN GEONATURE DB
        """

        ## if existing, delete all tables already uploaded which have the same id_import suffix
        delete_tables(id_import, ARCHIVES_SCHEMA_NAME, IMPORTS_SCHEMA_NAME)
        DB.session.commit()

        ## create user table classes (1 for gn_import_archives schema, 1 for gn_imports schema) corresponding to the user file structure (csv)
        user_class_gn_import_archives = generate_user_table_class(\
            ARCHIVES_SCHEMA_NAME, table_names['archives_table_name'], pk_name, columns, id_import, schema_type='archives')
        user_class_gn_imports = generate_user_table_class(\
            IMPORTS_SCHEMA_NAME, table_names['imports_table_name'], pk_name, columns, id_import, schema_type='gn_imports')

        ## create 2 empty tables in geonature db (in gn_import_archives and gn_imports schemas)
        engine = DB.engine
        user_class_gn_import_archives.__table__.create(bind=engine, checkfirst=True)
        user_class_gn_imports.__table__.create(bind=engine, checkfirst=True)

        ## fill the user table (copy_from function is equivalent to COPY function of postgresql)
        conn = engine.raw_connection()
        cur = conn.cursor()

        logger.info('* START COPY FROM CSV TO ARCHIVES SCHEMA')
        load_csv_to_db(full_path, cur, table_names['archives_full_table_name'], separator, columns)
        logger.info('* END COPY FROM CSV TO ARCHIVES SCHEMA')

        logger.info('* START COPY FROM CSV TO IMPORTS SCHEMA')
        load_csv_to_db(full_path, cur, table_names['imports_full_table_name'], separator, columns)
        logger.info('* END COPY FROM CSV TO IMPORTS SCHEMA')

        conn.commit()
        conn.close()
        cur.close()

        """
        FILLS CorImportArchives AND UPDATES TImports
        """
        
        delete_import_CorImportArchives(id_import)
        cor_import_archives = CorImportArchives(id_import=id_import, table_archive=table_names['archives_table_name'])
        DB.session.add(cor_import_archives)

        # update gn_import.t_imports with cleaned file name and step = 2
        DB.session.query(TImports)\
            .filter(TImports.id_import==id_import)\
            .update({
                TImports.import_table: table_names['archives_table_name'],
                TImports.step: 2,
                TImports.id_dataset: int(metadata['datasetId']),
                TImports.srid: int(metadata['srid']),
                TImports.format_source_file: report['file_format'],
                TImports.source_count: report['row_count']-1
                })
        
        DB.session.commit()

        logger.info('*** END UPLOAD USER FILE')

        return {
            "importId": id_import,
            "columns": columns,
        },200
               
    except psycopg2.errors.BadCopyFileFormat as e:
        logger.exception(e)
        DB.session.rollback()
        if is_id_import:
            delete_tables(id_import, ARCHIVES_SCHEMA_NAME, IMPORTS_SCHEMA_NAME)
        DB.session.commit()
        errors = []
        errors.append({
                'code': 'psycopg2.errors.BadCopyFileFormat',
                'message': 'Erreur probablement due à un problème de separateur',
                'message_data': e.diag.message_primary
        })
        logger.error(errors)
        return errors,400

    except Exception as e:
        logger.error('*** ERROR WHEN POSTING FILE')
        logger.exception(e)
        DB.session.rollback()
        if is_id_import:
            delete_tables(id_import, ARCHIVES_SCHEMA_NAME, IMPORTS_SCHEMA_NAME)
        DB.session.commit()
        raise GeonatureImportApiError(\
            message='INTERNAL SERVER ERROR : Erreur pendant l\'enregistrement du fichier - contacter l\'administrateur',
            details=str(e))
    finally:
        if is_file_saved:
            os.remove(full_path)
        DB.metadata.clear()
        DB.session.close()


@blueprint.route('/mapping/<import_id>', methods=['GET', 'POST'])
@permissions.check_cruved_scope('C', True, module_code="IMPORT")
@json_resp
def postMapping(info_role, import_id):
    try:

        ### INITIALIZE VARIABLES

        logger.info('*** START CORRESPONDANCE MAPPING')

        errors = []
        IMPORTS_SCHEMA_NAME = blueprint.config['IMPORTS_SCHEMA_NAME']
        ARCHIVES_SCHEMA_NAME = blueprint.config['ARCHIVES_SCHEMA_NAME']
        PREFIX = blueprint.config['PREFIX']
        index_col = ''.join([PREFIX,'pk'])
        table_names = get_table_names(ARCHIVES_SCHEMA_NAME, IMPORTS_SCHEMA_NAME, int(import_id))
        engine = DB.engine
        column_names = get_table_info(table_names['imports_table_name'], 'column_name')
        data = dict(request.get_json())
        MISSING_VALUES = ['', 'NA', 'NaN', 'na'] # mettre en conf
        DEFAULT_COUNT_VALUE = 1 # mettre en conf
        MODULE_URL = blueprint.config["MODULE_URL"]
        DIRECTORY_NAME = blueprint.config["UPLOAD_DIRECTORY"]

        logger.debug('import_id = %s', import_id)
        logger.debug('DB tabel name = %s', table_names['imports_table_name'])

        # get synthese fields filled in the user form:
        selected_columns = {key:value for key, value in data.items() if value}
        selected_user_cols = [*list(selected_columns.values())]
        logger.debug('selected columns in correspondance mapping = %s', selected_columns)

        # choose pandas if small dataset
        
        nrows = get_row_number(ARCHIVES_SCHEMA_NAME, IMPORTS_SCHEMA_NAME, int(import_id))
        
        logger.debug('row number = %s', nrows)
        if nrows < 200000:
            df_type = 'pandas'
        else:
            df_type = 'dask'
        logger.info('type of dataframe = %s', df_type)
        
        

        # extract
        logger.info('* START EXTRACT FROM DB TABLE TO PYTHON')

        df = extract(table_names['imports_table_name'], IMPORTS_SCHEMA_NAME, column_names, index_col, import_id)

        if df_type == 'pandas':
            df = compute_df(df)

        logger.info('* END EXTRACT FROM DB TABLE TO PYTHON')


        ### TRANSFORM (data checking and cleaning)

        logger.info('* START DATA CLEANING')
        transform_errors = data_cleaning(df, selected_columns, MISSING_VALUES, DEFAULT_COUNT_VALUE, df_type)

        if len(transform_errors) > 0:
            for error in transform_errors:
                logger.debug('USER ERRORS : %s', error['message'])
                errors.append(error)

        if 'temp' in df.columns:
            df = df.drop('temp', axis=1)

        logger.info('* END DATA CLEANING')


        ### LOAD (from Dask dataframe to postgresql table, with d6tstack pd_to_psql function)
        
        logger.info('* START LOAD PYTHON DATAFRAME TO DB TABLE')
        df = load(df, table_names['imports_table_name'], IMPORTS_SCHEMA_NAME, table_names['imports_full_table_name'], import_id, engine, index_col, df_type)
        logger.info('* END LOAD PYTHON DATAFRAME TO DB TABLE')
        

        ### UPDATE METADATA

        DB.session.query(TImports)\
            .filter(TImports.id_import==import_id)\
            .update({
                TImports.step: 3,
                })
        
        DB.session.commit()
        DB.session.close()

        n_invalid_rows = str(df['gn_is_valid'].astype(str).str.contains('False').sum())

        logger.info('*** END CORRESPONDANCE MAPPING')


        """
        ### importer les données dans synthese
        selected_columns = {key:value for key, value in data.items() if value}

        selected_synthese_cols = ','.join(selected_columns.keys())
        selected_user_cols = ','.join(selected_columns.values())

        # ok ça marche
        print('fill synthese')
        DB.session.execute("INSERT INTO gn_synthese.synthese ({}) SELECT {} FROM {} WHERE gn_is_valid=TRUE;".format(selected_synthese_cols,selected_user_cols,table_names['imports_full_table_name']))
        #INSERT INTO gn_synthese.synthese (cd_nom,nom_cite,date_min,date_max) SELECT species_id,nom_scientifique,my_timestamp::timestamp,date_max FROM gn_imports.i_data_pf_observado_corrected_303 WHERE gn_is_valid=TRUE;
        print('synthese filled')
        DB.session.commit()      
        DB.session.close()
        """
        
        """
        if len(errors) > 0:
            return errors,400
        """

        return {
            'user_error_details' : transform_errors,
            'n_user_errors' : n_invalid_rows
        }

    except Exception as e:
        logger.error('*** ERROR IN CORRESPONDANCE MAPPING')
        logger.exception(e)
        DB.session.rollback()
        DB.session.close()

        n_loaded_rows = DB.session.execute(
            "SELECT count(*) FROM {}".format(table_names['imports_full_table_name'])
            ).fetchone()[0]
        if n_loaded_rows == 0:
            logger.error('Table %s vide à cause d\'une erreur de copie, refaire l\'upload et le mapping', table_names['imports_full_table_name'])
            raise GeonatureImportApiError(\
                message='INTERNAL SERVER ERROR :: Erreur pendant le mapping de correspondance :: Table {} vide à cause d\'une erreur de copie, refaire l\'upload et le mapping, ou contactez l\'administrateur du site'.format(table_names['imports_full_table_name']),
                details='')
    
        raise GeonatureImportApiError(\
            message='INTERNAL SERVER ERROR : Erreur pendant le mapping de correspondance - contacter l\'administrateur',
            details=str(e))


@blueprint.route('/syntheseInfo', methods=['GET'])
@permissions.check_cruved_scope('C', True, module_code="IMPORT")
@json_resp
def getSyntheseInfo(info_role):
    try:
        EXCLUDED_SYNTHESE_FIELDS_FRONT = blueprint.config['EXCLUDED_SYNTHESE_FIELDS_FRONT']
        NOT_NULLABLE_SYNTHESE_FIELDS = blueprint.config['NOT_NULLABLE_SYNTHESE_FIELDS']

        synthese_info = []

        data = DB.session.execute(\
                    "SELECT column_name,is_nullable,column_default,data_type,character_maximum_length\
                     FROM INFORMATION_SCHEMA.COLUMNS\
                     WHERE table_name = 'synthese';"\
        )

        for d in data:
            if d.column_name not in EXCLUDED_SYNTHESE_FIELDS_FRONT:
                if d.column_name in NOT_NULLABLE_SYNTHESE_FIELDS:
                    is_nullabl = 'NO'
                else:
                    is_nullabl = 'YES'
                prop = {
                    "column_name": d.column_name,
                    "is_nullable": is_nullabl,
                    "data_type": d.data_type,
                    "character_maximum_length": d.character_maximum_length,
                }
                synthese_info.append(prop)
        #names2 = ['nom_cite', 'date_min', 'date_max']
        #print(synthese_info)
        return synthese_info, 200
    except Exception:
        raise
        return 'INTERNAL SERVER ERROR ("getSyntheseInfo() error"): contactez l\'administrateur du site', 500


"""
@blueprint.route('/return_to_list/<import_id>', methods=['GET'])
@permissions.check_cruved_scope('C', True, module_code="IMPORT")
@json_resp
def return_to_list(info_role, import_id):
    try:
        
        #Si import_id is not undefined, effacer ligne dans timports_id, cor_role_import, cor_archive_import si step = 1
        

        return server_response, 200
    except Exception:
        return 'INTERNAL SERVER ERROR ("delete_TImportRow() error"): contactez l\'administrateur du site', 500
"""