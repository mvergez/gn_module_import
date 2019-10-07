import pandas as pd
import datetime
import dask
import dask.dataframe as dd

from .utils import fill_col, fill_map, set_is_valid, set_invalid_reason, set_user_error
from ..wrappers import checker
from ..logs import logger

import pdb


def is_negative_date(value):
    try:
        if type(value) != pd.Timedelta:
            return True
        else:
            if value.total_seconds() >= 0:
                return True
            else:
                return False
    except TypeError:
        return True


@checker('Data cleaning : dates checked')
def check_dates(df, added_cols, selected_columns, dc_user_errors, synthese_info):

    try:

        logger.info('CHECKING DATES :')
        # get user synthese fields having timestamp type
        date_fields = [field for field in synthese_info if synthese_info[field]['data_type'] == 'timestamp without time zone']

        ## date_min and date_max :

        # set date_max (=if data_max not existing, then set equal to date_min)
        if 'date_max' not in date_fields:
            logger.info('- date_max not provided : set date_max = date_min')
            added_cols['date_max'] = selected_columns['date_min']
            df['date_max'] = df[selected_columns['date_min']] # utile?
            synthese_info.update({'date_max': synthese_info['date_min']}) # utile?

        # ajouter verif que date min <= date max
        if 'date_min' in date_fields and 'date_max' in date_fields:

            logger.info('- checking date_min (= %s user column) <= date_max (= %s user column)', selected_columns['date_min'], selected_columns['date_max'])

            df['check_dates'] = ''
            #pd.to_datetime(df[selected_columns['date_min']], errors='coerce').fillna(pd.np.nan)
            df['check_dates'] = df[selected_columns['date_max']] - df[selected_columns['date_min']]
            df['temp'] = ''
            df['temp'] = df['temp']\
                .where(
                    cond=df['check_dates'].apply(lambda x: is_negative_date(x)), 
                    other=False)\
                .map(fill_map)\
                .astype('bool')
            
            set_is_valid(df, 'temp')
            set_invalid_reason(df, 'temp', 'date_min > date_max ({} columns)', ','.join([selected_columns['date_min'],selected_columns['date_max']]))
            n_date_min_sup = df['temp'].astype(str).str.contains('False').sum()

            logger.info('%s date_min (= %s user column) > date_max (= %s user column) errors detected', n_date_min_sup, selected_columns['date_min'], selected_columns['date_max'])

            if n_date_min_sup > 0:
                set_user_error(dc_user_errors, 7, selected_columns['date_min'], n_date_min_sup)    
        

        ## meta_create_date and meta_update_date :



        if 'check_dates' in df.columns:
            df = df.drop('check_dates', axis=1)


    except Exception:
        raise