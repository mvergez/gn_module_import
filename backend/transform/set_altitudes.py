from ..wrappers import checker
from ..logs import logger
from ..db.queries.altitudes import (
    create_column,
    generate_altitudes
)
from ..utils.utils import create_col_name


@checker('Data cleaning : altitudes created')
def set_altitudes(df, selected_columns, import_id, schema_name, full_table_name, table_name, index_col, is_generate_alt):

    logger.info('generating altitudes :')

    if is_generate_alt:

        if 'altitude_min' not in selected_columns.keys():
            create_col_name(df, selected_columns, 'altitude_min', 'gn_altitude_min', import_id)
            create_column(
                full_table_name = full_table_name, 
                alt_col = selected_columns['altitude_min'])

        generate_altitudes(
            schema = schema_name, 
            table = table_name, 
            alt_col = selected_columns['altitude_min'], 
            table_pk = index_col,
            geom_col = 'the_geom_local')

        if 'altitude_max' not in selected_columns.keys():
            create_col_name(df, selected_columns, 'altitude_max', 'gn_altitude_max', import_id)
            create_column(
                full_table_name = full_table_name, 
                alt_col = selected_columns['altitude_max'])
        
        generate_altitudes(
            schema = schema_name, 
            table = table_name, 
            alt_col = selected_columns['altitude_max'], 
            table_pk = index_col,
            geom_col = 'the_geom_local')