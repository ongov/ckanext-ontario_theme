
# -*- coding: utf-8 -*-
"""
Server-side Ajax for brushable histograms in CKAN DataTables view.

- Accepts DataTables paging/ordering.
- Accepts histogram brush ranges (odcRanges).
- Applies numeric range filters via datastore_search_sql (BETWEEN).
- Returns rows keyed by Data Dictionary field ids and ALWAYS includes "_id".
- Returns filtered histogram bin counts per numeric field (cross-filter AND),
  aligned to the full-distribution domains provided by the client.
- Excludes the index column "_id" from histogram computation/rendering.
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

_UUID_RE = re.compile(r'^[0-9a-fA-F\-]{36}$')

def _quote_ident(ident: str) -> str:
    return '"' + ident.replace('"', '""') + '"'

def _is_numeric_type(ftype: str) -> bool:
    t = (ftype or '').lower()
    return bool(re.match(
        r'^(?:int|integer|int2|int4|int8|smallint|bigint|float|float4|float8|real|double(?:\s+precision)?|numeric|decimal|number)$',
        t
    ))

def _is_integer_type(ftype: str) -> bool:
    t = (ftype or '').lower()
    return bool(re.match(r'^(?:int|integer|int2|int4|int8|smallint|bigint)$', t))

_BRACKETED_RE = re.compile(r'^odcRanges\[(\d+)\]\[(\w+)\]$')

def _parse_bracketed_ranges(values) -> List[Dict[str, Any]]:
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
    if not _UUID_RE.match(resource_id):
        return jsonify({'error': 'Invalid resource_id'}), 400

    try:
        draw = int(request.values.get('draw', 1))
        start = max(0, int(request.values.get('start', 0)))
        length = int(request.values.get('length', 50))
    except ValueError:
        return jsonify({'error': 'Invalid pagination params'}), 400
    length = max(1, min(length, 1000))

    order_col_idx = request.values.get('order[0][column]')
    order_dir = request.values.get('order[0][dir]', 'asc')

    ranges_json = request.values.get('odcRanges')
    ranges: List[Dict[str, Any]] = []
    if ranges_json:
        try:
            parsed = json.loads(ranges_json)
            if isinstance(parsed, list):
                ranges = parsed
        except Exception:
            ranges = []
    if not ranges:
        ranges = _parse_bracketed_ranges(request.values)

    context = {'user': g.user, 'ignore_auth': False}

    try:
        info = toolkit.get_action('datastore_info')(context, {'id': resource_id})
    except NotAuthorized:
        return jsonify({'error': 'Not authorized'}), 403
    except Exception as e:
        return jsonify({'error': f'datastore_info failed: {e}'}), 500

    fields = info.get('fields', []) or []
    allowed_types = {f['id']: f.get('type', '') for f in fields}
    dict_ids: List[str] = [f['id'] for f in fields]

    proj_ids: List[str] = ['_id'] + [fid for fid in dict_ids if fid != '_id']

    # WHERE clauses (AND across numeric brushes), ignore any ranges on _id
    where_clauses: List[str] = []
    for r in ranges:
        fld = r.get('field')
        if not fld or fld == '_id' or fld not in allowed_types:
            continue
        if not _is_numeric_type(allowed_types[fld]):
            continue
        try:
            minv = float(r.get('min'))
            maxv = float(r.get('max'))
        except (TypeError, ValueError):
            continue
        if not (math.isfinite(minv) and math.isfinite(maxv)):
            continue
        if _is_integer_type(allowed_types[fld]):
            minv = math.floor(minv)
            maxv = math.ceil(maxv)
        where_clauses.append(f"{_quote_ident(fld)} BETWEEN {minv} AND {maxv}")

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    order_sql = ""
    try:
        if order_col_idx is not None:
            idx = int(order_col_idx)
            if 0 <= idx < len(proj_ids):
                sort_fld = proj_ids[idx]
                order_sql = f'ORDER BY {_quote_ident(sort_fld)} {"DESC" if order_dir=="desc" else "ASC"}'
    except ValueError:
        pass

    # Page query
    select_cols = ", ".join(_quote_ident(fid) for fid in proj_ids)
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

    rows = page_res.get('records', []) or []
    if rows and isinstance(rows[0], list):
        rows = [dict(zip(proj_ids, r)) for r in rows]
    if rows and isinstance(rows[0], dict) and '_id' not in rows[0]:
        for r in rows:
            r.setdefault('_id', None)

    payload = {
        'draw': draw,
        'recordsTotal': records_total,
        'recordsFiltered': records_filtered,
        'data': rows,
        'records': rows
    }

    # Filtered histogram overlay for ALL eligible numeric columns (exclude _id)
    try:
        want_hist = request.values.get('odcHist') in ('1', 'true', 'True')
        if want_hist:
            try:
                bin_count = int(request.values.get('odcBinCount', 24))
                bin_count = max(1, min(bin_count, 96))
            except Exception:
                bin_count = 24

            fields_req_json = request.values.get('odcHistFields') or '[]'
            domains_json = request.values.get('odcHistDomain') or '{}'
            try:
                fields_req = json.loads(fields_req_json) if fields_req_json else []
            except Exception:
                fields_req = []
            try:
                domains = json.loads(domains_json) if domains_json else {}
            except Exception:
                domains = {}

            # Only numeric columns present in the dictionary, excluding _id
            fields_numeric = [
                f for f in fields_req
                if f != '_id' and f in allowed_types and _is_numeric_type(allowed_types[f])
            ]

            histograms: Dict[str, Any] = {}
            base_where_parts = list(where_clauses)  # AND across all brushes

            for fld in fields_numeric:
                ident_res = _quote_ident(resource_id)
                ident_fld = _quote_ident(fld)

                # Use client domain for alignment; fallback if missing
                dm = domains.get(fld, {})
                minv = dm.get('min'); maxv = dm.get('max')
                if (minv is None) or (maxv is None):
                    sql_mm = f'''
                        SELECT MIN({ident_fld}) AS minv, MAX({ident_fld}) AS maxv
                        FROM {ident_res}
                        WHERE {ident_fld} IS NOT NULL
                    '''.strip()
                    try:
                        mm_res = toolkit.get_action('datastore_search_sql')(context, {'sql': sql_mm})
                        if mm_res.get('records'):
                            minv = float(mm_res['records'][0]['minv'])
                            maxv = float(mm_res['records'][0]['maxv'])
                    except Exception as e:
                        log.warning("domain fallback failed for %s: %s", fld, e)
                        minv = None; maxv = None

                if (minv is None) or (maxv is None) or (not (math.isfinite(minv) and math.isfinite(maxv))) or (maxv <= minv):
                    continue

                # WHERE for bins: all brushes + this field not null
                where_parts = list(base_where_parts)
                where_parts.append(f"{ident_fld} IS NOT NULL")
                where_for_bins = "WHERE " + " AND ".join(where_parts)

                sql_bins = f'''
                    WITH params AS (
                        SELECT {float(minv)}::double precision AS minv,
                               {float(maxv)}::double precision AS maxv
                    ),
                    filtered AS (
                        SELECT {ident_fld} AS v
                        FROM {ident_res}
                        {where_for_bins}
                    )
                    SELECT width_bucket(v, (SELECT minv FROM params), (SELECT maxv FROM params), {int(bin_count)}) AS bin,
                           COUNT(*) AS count
                    FROM filtered
                    GROUP BY bin
                    ORDER BY bin
                '''.strip()

                try:
                    bins_res = toolkit.get_action('datastore_search_sql')(context, {'sql': sql_bins})
                    rows_bins = bins_res.get('records', []) or []
                    bins = [{'bin': int(r['bin']), 'count': int(r['count'])} for r in rows_bins if r.get('bin') is not None]
                    histograms[fld] = {'min': float(minv), 'max': float(maxv), 'binCount': int(bin_count), 'bins': bins}
                except Exception as e:
                    log.warning("histogram bins failed for %s: %s", fld, e)

            if histograms:
                payload['histograms'] = histograms

    except Exception as e:
        log.warning("odcHist processing failed: %s", e)

    return jsonify(payload)
