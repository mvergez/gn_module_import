import pandas as pd 
import numpy as np
import datetime

from .utils import fill_map, set_is_valid, set_invalid_reason, set_user_error
from ..wrappers import checker
from ..logs import logger

import pdb


def format_missing(df, selected_columns, synthese_info, missing_values):

    try :
        fields = [field for field in synthese_info]

        for field in fields:
            logger.info('- formatting eventual missing values in %s synthese column (= %s user column)', field, selected_columns[field])
            df[selected_columns[field]] = df[selected_columns[field]].replace(missing_values,pd.np.nan).fillna(value=pd.np.nan)

    except Exception as e:
        pdb.set_trace()
        raise 


@checker('Data cleaning : missing values checked')
def check_missing(df, selected_columns, dc_user_errors, synthese_info, missing_values):

    try:
        logger.info('CHECKING MISSING VALUES : ')

        format_missing(df, selected_columns, synthese_info, missing_values)

        fields = [field for field in synthese_info if synthese_info[field]['is_nullable'] == 'NO']

        #df[selected_columns[field]].isnull().any()

        for field in fields:

            logger.info('- checking missing values in %s synthese column (= %s user column)', field, selected_columns[field])
            
            if df[selected_columns[field]].isnull().any():

                df['temp'] = ''
                df['temp'] = df[selected_columns[field]]\
                    .replace(missing_values,np.nan)\
                    .notnull()\
                    .map(fill_map)\
                    .astype('bool')

                set_is_valid(df, 'temp')
                set_invalid_reason(df, 'temp', 'missing value in {} column', selected_columns[field])
                n_missing_value = df['temp'].astype(str).str.contains('False').sum()

                df.drop('temp',axis=1)

                logger.info('%s missing values detected for %s synthese column (= %s user column)', n_missing_value, field, selected_columns[field])

                if n_missing_value > 0:
                    set_user_error(dc_user_errors, 5, selected_columns[field], n_missing_value)
            else:
                logger.info('0 missing values detected for %s synthese column (= %s user column)', field, selected_columns[field])


    except Exception:
        raise