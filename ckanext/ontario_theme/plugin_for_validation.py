# encoding: utf-8

from typing import Type, Any, Dict

from .column_types import ColumnType, _standard_column_types

# NB: # Dict not needed for python 3.10 (https://stackoverflow.com/questions/67701167/how-to-use-quoted-type-annotations-for-base-class-in-python-3-8)
_column_types: Dict[str, Type[ColumnType]] = {}


def tabledesigner_column_type(field: Dict[str, Any]) -> ColumnType:
    """
    return column type object (fall back to text if not found)
    """
    if 'info' in field:
        info = field['info']
        if info['type_override']:
            type_override =  info['type_override']
        else:
            type_override = 'text'
    else:
        type_override = field['type']
        info = field

    coltypes = dict(_standard_column_types)

    return _column_types.get(
        type_override,
        coltypes.get(type_override)
    )(info)


def reformat_ui_dict(o):
    ''' Reformats the dictionary object from the UI form
    into the structure used by ckanext-validation. Also
    replaces PostgreSQL data types with their Fricionless
    Data equivalents.

    :param o: the array containing the dictionary object

    '''
    schema_obj = {}
    typeArray = []
    for el in o:
        if el['id'] != "_id":
            if 'info' in el:
                el['type'] = tabledesigner_column_type(el).table_schema_type

                del el['info']
            else:
                el['type'] = tabledesigner_column_type(el).table_schema_type

            # Switch 'id' key name to 'name'
            el['name'] = el['id']
            del el['id']

            typeArray.append(el)

    schema_obj['fields'] = typeArray

    return schema_obj