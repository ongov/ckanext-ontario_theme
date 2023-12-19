from __future__ import annotations

from typing import Type, Callable, Any, List
# from collections.abc import Iterable, Mapping

# from ckanext.datastore.backend.postgres import identifier, literal_string

# from .column_constraints import ColumnConstraint


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

@_standard_column('text')
class TextColumn(ColumnType):
    label = _('Text')
    description = _('Unicode text of any length')
    example = _('free-form text')
    table_schema_type = 'string'
    table_schema_format = 'default'