
# -*- coding: utf-8 -*-
"""
Server-side Ajax for brushable histograms in CKAN DataTables view.
- Accepts DataTables paging/ordering.
- Accepts histogram brush ranges (odcRanges).
- Applies numeric range filters via datastore_search_sql (BETWEEN).
- Returns rows keyed by Data Dictionary field ids and ALWAYS includes "_id".
"""

import math
import re
import json
from typing import List, Dict, Any
from flask import Blueprint, request, jsonify
from ckan.plugins import toolkit
from ckan.common import g
from ckan.logic import NotAuthorized
import logging

log = logging.getLogger(__name__)

bp = Blueprint('odc_datatables', __name__)
bp.url_prefix = '/odc'  # match JS ajaxPrefix: '/odc/datatables/ajax'

# Safer UUID table-name validator (CKAN datastore tables are UUIDs)
_UUID_RE = re.compile(r'^[0-9a-fA-F-]{36}$')

def _quote_ident(ident: str) -> str:
    """Safe double-quoting for Postgres identifiers."""
    return '"' + ident.replace('"', '""') + '"'

def _is_numeric_type(ftype: str) -> bool:
    t = (ftype or '').lower()
    return bool(re.match(
        r'^(?:int'
        r'|integer'
        r'|int2'
        r'|int4'
        r'|int8'
        r'|smallint'
        r'|bigint'
        r'|float'
        r'|float4'
        r'|float8'
        r'|real'
        r'|double(?:\s+precision)?'
        r'|numeric'
        r'|decimal'
        r'|number)$',
        t
    ))

# Fallback parser for jQuery's bracketed serialization:
# odcRanges[0][field]=... & odcRanges[0][min]=... & odcRanges[0][max]=...
_BRACKETED_RE = re.compile(r'^odcRanges\[(\d+)\]\[(\w+)\]$')

def _parse_bracketed_ranges(values) -> List[Dict[str, Any]]:
    """
    Rebuilds odcRanges from keys like 'odcRanges[0][min]' produced by jQuery/DataTables.
    """
    tmp: Dict[int, Dict[str, Any]] = {}
    for k in values.keys():
        m = _BRACKETED_RE.match(k)
        if not m:
            continue
        idx = int(m.group(1))
        key = m.group(2)
        tmp.setdefault(idx, {})[key] = values.get(k)
    return [tmp[i] for i in sorted(tmp.keys())]

@bp.route('/datatables/ajax/<resource_id>', methods=['POST', 'GET'])
def odc_datatables_ajax(resource_id):
    # --- Validate resource_id (datastore table name) ---
    if not _UUID_RE.match(resource_id):
        return jsonify({'error': 'Invalid resource_id'}), 400

    # --- DataTables params ---
    try:
        draw = int(request.values.get('draw', 1))
        start = max(0, int(request.values.get('start', 0)))
        length = int(request.values.get('length', 50))
    except ValueError:
        return jsonify({'error': 'Invalid pagination params'}), 400
    length = max(1, min(length, 1000))  # cap

    order_col_idx = request.values.get('order[0][column]')
    order_dir = request.values.get('order[0][dir]', 'asc')

    # Try JSON string first (when frontend sends data.odcRanges = JSON.stringify([...]))
    ranges_json = request.values.get('odcRanges')
    ranges: List[Dict[str, Any]] = []
    if ranges_json:
        try:
            parsed = json.loads(ranges_json)
            if isinstance(parsed, list):
                ranges = parsed
        except Exception:
            ranges = []

    # Fallback to bracketed form (when frontend sent array-of-objects natively)
    if not ranges:
        ranges = _parse_bracketed_ranges(request.values)

    # --- Action API context with current user for auth ---
    context = {'user': g.user, 'ignore_auth': False}

    # --- Data Dictionary: whitelist + projection keys ---
    try:
        info = toolkit.get_action('datastore_info')(context, {'id': resource_id})
    except NotAuthorized:
        return jsonify({'error': 'Not authorized'}), 403
    except Exception as e:
        return jsonify({'error': f'datastore_info failed: {e}'}), 500

    fields = info.get('fields', []) or []
    allowed_types = {f['id']: f.get('type', '') for f in fields}
    dict_ids: List[str] = [f['id'] for f in fields]  # user/schema field ids (may or may not include "_id")

    # --- Build projection order: ALWAYS start with "_id" ---
    proj_ids: List[str] = ['_id'] + [fid for fid in dict_ids if fid != '_id']

    # --- WHERE clauses from numeric brush ranges (AND across columns) ---
    where_clauses: List[str] = []
    for r in ranges:
        fld = r.get('field')
        if not fld or fld not in allowed_types:
            # If brushing sent a field not in dictionary, skip
            continue
        if not _is_numeric_type(allowed_types[fld]):
            # Skip non-numeric (e.g., text column "rule")
            continue
        try:
            minv = float(r.get('min'))
            maxv = float(r.get('max'))
        except (TypeError, ValueError):
            continue
        if not (math.isfinite(minv) and math.isfinite(maxv)):
            continue
        where_clauses.append(f"{_quote_ident(fld)} BETWEEN {minv} AND {maxv}")

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    # --- ORDER BY: map column index to projection ids (0 => '_id') ---
    order_sql = ""
    try:
        if order_col_idx is not None:
            idx = int(order_col_idx)
            if 0 <= idx < len(proj_ids):
                sort_fld = proj_ids[idx]
                # Only allow sorting by fields that exist in the table; '_id' is safe
                order_sql = f'ORDER BY {_quote_ident(sort_fld)} {"DESC" if order_dir=="desc" else "ASC"}'
    except ValueError:
        pass

    log.debug("request.values: %s", dict(request.values))
    log.info("odcRanges: %s", ranges)
    log.info("WHERE clauses: %s", where_clauses)
    log.info("ORDER BY: %s", order_sql)

    # --- Projection SELECT (quote every identifier) ---
    select_cols = ", ".join(_quote_ident(fid) for fid in proj_ids)

    # --- Page query ---
    sql_page = f'''
    SELECT {select_cols}
    FROM {_quote_ident(resource_id)}
    {where_sql} {order_sql}
    LIMIT {length} OFFSET {start}
    '''.strip()

    try:
        page_res = toolkit.get_action('datastore_search_sql')(context, {'sql': sql_page})
    except NotAuthorized:
        return jsonify({'error': 'Not authorized'}), 403
    except Exception as e:
        return jsonify({'error': f'datastore_search_sql failed: {e}'}), 500

    # --- Totals ---
    sql_total = f'SELECT COUNT(*) AS c FROM {_quote_ident(resource_id)}'
    sql_filtered = f'SELECT COUNT(*) AS c FROM {_quote_ident(resource_id)} {where_sql}'

    try:
        total_res = toolkit.get_action('datastore_search_sql')(context, {'sql': sql_total})
        filt_res = toolkit.get_action('datastore_search_sql')(context, {'sql': sql_filtered})
    except NotAuthorized:
        return jsonify({'error': 'Not authorized'}), 403
    except Exception as e:
        return jsonify({'error': f'count failed: {e}'}), 500

    records_total = int(total_res['records'][0]['c']) if total_res.get('records') else 0
    records_filtered = int(filt_res['records'][0]['c']) if filt_res.get('records') else records_total

    # --- Rows: CKAN returns array-of-objects (ideal) OR array-of-arrays (defensive fix) ---
    rows = page_res.get('records', []) or []
    # If arrays, convert to objects keyed by proj_ids
    if rows and isinstance(rows[0], list):
        rows = [dict(zip(proj_ids, r)) for r in rows]
    # If objects, ensure '_id' is present; if missing, add with None
    if rows and isinstance(rows[0], dict) and '_id' not in rows[0]:
        for r in rows:
            r.setdefault('_id', None)

    # Return DataTables server-side shape; also alias 'records' for safety
    payload = {
        'draw': draw,
        'recordsTotal': records_total,
        'recordsFiltered': records_filtered,
        'data': rows,   # default dataSrc
        'records': rows # in case viewer uses 'records' as dataSrc
    }
    return jsonify(payload)
