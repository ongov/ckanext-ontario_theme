from __future__ import annotations

from typing import Type, Callable, Any, Dict

def _(x: str):
    return x


_standard_column_types = {}


def _standard_column(
        key: str) -> "Callable[[Type[ColumnType]], Type[ColumnType]]":
    def register(cls: "Type[ColumnType]"):
        _standard_column_types[key] = cls
        return cls
    return register

class ColumnType:
    label = 'undefined'
    # some defaults to save repetition in subclasses
    datastore_type = 'text'
    html_input_type = 'text'

    def __init__(            
            self,
            info: Dict[str, Any]
            ):
        self.colname = info.get('id', '')
        self.info = info

@_standard_column('text')
class TextColumn(ColumnType):
    label = _('Text')
    description = _('Unicode text of any length')
    example = _('free-form text')
    table_schema_type = 'string'
    table_schema_format = 'default'

@_standard_column('numeric')
class NumericColumn(ColumnType):
    label = _('Numeric')
    description = _('Number with arbitrary precision (any number of '
                    'digits before and after the decimal)')
    example = '2.01'
    datastore_type = 'numeric'
    table_schema_type = 'number'

@_standard_column('integer')
class IntegerColumn(ColumnType):
    label = _('Integer')
    description = _('Whole numbers with no decimal')
    example = '21'
    datastore_type = 'int8'
    table_schema_type = 'integer'

@_standard_column('boolean')
class BooleanColumn(ColumnType):
    label = _('Boolean')
    description = _('True or false values')
    example = 'false'
    datastore_type = 'boolean'
    table_schema_type = 'boolean'

@_standard_column('date')
class DateColumn(ColumnType):
    label = _('Date')
    description = _('Date without time of day')
    example = '2024-01-01'
    datastore_type = 'date'
    table_schema_type = 'date'

@_standard_column('timestamp')
class TimestampColumn(ColumnType):
    label = _('Timestamp')
    description = _('Date and time without time zone')
    example = '2024-01-01 12:00:00'
    datastore_type = 'timestamp'
    table_schema_type = 'time'

def column_types(
            self, existing_types: Dict[str, Type[ColumnType]]
            ) -> Dict[str, Type[ColumnType]]:
        """
        return a {tdtype string value: ColumnType subclasses, ...} dict
        existing_types is the standard column types dict, possibly modified
        by other IColumnTypes plugins later in the plugin list (earlier
        plugins may modify types added/removed/updated by later plugins)
        ColumnType subclasses are used to set underlying datastore types,
        validation rules, input widget types, template snippets, choice
        lists, examples, help text and control other table designer
        features.
        """
        return existing_types