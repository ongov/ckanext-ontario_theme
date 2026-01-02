
(function (root, factory) {
  if (typeof define === 'function' && define.amd) define(['jquery'], factory);
  else if (typeof exports === 'object') module.exports = factory(require('jquery'));
  else root.OdcHistograms = factory(root.jQuery);
}(this, function ($) {
  'use strict';

  const DEFAULTS = {
    binCount: 24, height: 44,
    margin: { top: 4, right: 8, bottom: 18, left: 8 },
    pageLength: 50, smallThreshold: 50,
    serverBins: true, ajaxPrefix: null, debug: true,
    theme: {
      barFill: 'var(--ontario-colour-primary, #1a5a96)',
      axisColor: 'var(--ontario-colour-ink, #1a1a1a)',
      brushFill: 'rgba(26,90,150,0.18)',
      brushStroke: 'var(--ontario-colour-primary, #1a5a96)'
    }
  };
  const tableRangeState = new Map();

  function norm(opts) {
    opts = opts || {};
    const o = Object.assign({}, DEFAULTS, opts);
    o.theme = Object.assign({}, DEFAULTS.theme, opts.theme || {});
    o.margin = Object.assign({}, DEFAULTS.margin, opts.margin || {});
    return o;
  }
  function getCkanBaseUrl() { return window.location.origin; }
  function parseNum(v) {
    if (v == null) return null;
    if (typeof v === 'number' && isFinite(v)) return v;
    const s = String(v).trim(); if (!s) return null;
    const cleaned = s.replace(/[%,$€£\s]/g, '').replace(/,/g, '');
    const num = parseFloat(cleaned);
    return isNaN(num) ? null : num;
  }

  // -------- Column keys & types from CKAN Data Dictionary --------
  function getColumnKeys(dt) {
    // CKAN gdataDict: array of field dicts; header order is: _id + gdataDict
    if (Array.isArray(window.gdataDict) && window.gdataDict.length) {
      return ['_id'].concat(window.gdataDict.map(f => f.id));
    }
    try {
      return dt.columns().dataSrc().toArray();
    } catch (e) { return []; }
  }
  function getColumnTypes(dt) {
    if (Array.isArray(window.gdataDict) && window.gdataDict.length) {
      // Treat CKAN DataStore _id as an integer; then map dictionary types
      return ['integer'].concat(window.gdataDict.map(f => (f.type || '').toLowerCase()));
    }
    // Fallback: read type from the filter header row (if present)
    const types = [];
    const cols = dt.columns().indexes().toArray();
    const headerRows = dt.table().header().querySelectorAll('tr');
    const filterRow = headerRows[1];
    for (const i of cols) {
      const th = filterRow && filterRow.children[i] ? filterRow.children[i] : null;
      types.push((th && th.getAttribute('data-type') || '').toLowerCase());
    }
    // Default the first column (_id) to integer when unknown
    if (types.length && !types[0]) types[0] = 'integer';
    return types;
  }
  function isNumericType(t) {
    t = (t || '').toLowerCase();
    // Accept PostgreSQL integer & float aliases as numeric
    // int2/smallint, int4/integer, int8/bigint; float4/real, float8/double precision; number/decimal/numeric
    return /^(?:int|integer|int2|int4|int8|smallint|bigint|float|float4|float8|real|double(?:\s+precision)?|numeric|decimal|number)$/.test(t);
  }

  // -------- Ajax hook: send ranges --------
  function bindPreXhr($table, opts) {
    $table.off('preXhr.dt.odc').on('preXhr.dt.odc', function (e, settings, data) {
      const dt = $(settings.nTable).DataTable();
      const keys = getColumnKeys(dt);
      const rangesForTable = tableRangeState.get(dt.table().node().id) || [];

      const ranges = rangesForTable.map(r => ({
        field: keys[r.colIdx],
        colIndex: r.colIdx,
        min: r.min,
        max: r.max
      })).filter(rr => rr.field && isFinite(rr.min) && isFinite(rr.max));

      data.odcRanges = JSON.stringify(ranges);      // <-- send as JSON string
      data.columnNames = JSON.stringify(keys);

      if (opts.debug) {
        console.log('[preXhr] odcRanges=', ranges);
      }
    });
  }

  // -------- CKAN API bins --------
  async function fetchServerBins(resourceId, field, bins) {
    const identRes = `"${resourceId.replace(/"/g, '""')}"`;
    const identFld = `"${field.replace(/"/g, '""')}"`;
    const sql =
      `WITH mm AS (SELECT MIN(${identFld}) AS minv, MAX(${identFld}) AS maxv FROM ${identRes} WHERE ${identFld} IS NOT NULL)
       SELECT width_bucket(${identFld}, (SELECT minv FROM mm), (SELECT maxv FROM mm), ${bins}) AS bin,
              COUNT(*) AS count,
              (SELECT minv FROM mm) AS minv, (SELECT maxv FROM mm) AS maxv
       FROM ${identRes} WHERE ${identFld} IS NOT NULL
       GROUP BY bin ORDER BY bin`;
    const url = `${getCkanBaseUrl()}/api/3/action/datastore_search_sql?sql=${encodeURIComponent(sql)}`;
    const res = await $.getJSON(url);
    if (res && res.success && res.result && res.result.records && res.result.records.length) {
      const rows = res.result.records;
      const minv = Number(rows[0].minv);
      const maxv = Number(rows[0].maxv);
      const data = rows.map(r => ({ bin: Number(r.bin), count: Number(r.count) }));
      return { min: minv, max: maxv, bins: data, binCount: bins };
    }
    return null;
  }

  // -------- Rendering --------
  function renderHistogram(dt, i, values, opts, d3, min, max, countsFromServer) {
    const theme = opts.theme;
    const headerRows = dt.table().header().querySelectorAll('tr');
    const filterRow = headerRows[1];
    const fth = filterRow && filterRow.children[i] ? filterRow.children[i] : null;
    if (!fth) return;
    const th = $(fth); th.addClass('odc-numeric-filter').empty();

    const w = (function () { const rect = fth.getBoundingClientRect(); return Math.max(140, Math.floor(rect.width)); })() - opts.margin.left - opts.margin.right;
    const h = opts.height - opts.margin.top - opts.margin.bottom;
    const container = $('<div class="ods-histogram" aria-label="Histogram filter"></div>');
    const svgEl = $('<svg class="ods-histogram-svg" role="img"></svg>')
      .attr('width', w + opts.margin.left + opts.margin.right)
      .attr('height', h + opts.margin.top + opts.margin.bottom);
    container.append(svgEl); th.append(container);

    const svg = d3.select(svgEl[0]).append('g')
      .attr('transform', `translate(${opts.margin.left},${opts.margin.top})`);

    const x = d3.scaleLinear().domain([min, max]).range([0, w]);
    let bins;
    if (countsFromServer) {
      const bw = (max - min) / opts.binCount;
      const y = d3.scaleLinear().domain([0, d3.max(countsFromServer, d => d.count)]).nice().range([h, 0]);
      svg.selectAll('.bar')
        .data(countsFromServer).enter().append('rect').attr('class', 'bar')
        .attr('x', d => x(min + (d.bin - 1) * bw) + 1)
        .attr('y', d => y(d.count))
        .attr('width', Math.max(0, x(min + d.bin * bw) - x(min + (d.bin - 1) * bw) - 2))
        .attr('height', d => h - y(d.count))
        .attr('fill', theme.barFill);
      const xAxis = d3.axisBottom(x).ticks(4).tickSize(3);
      svg.append('g').attr('class', 'axis axis--x').attr('transform', `translate(0,${h})`).call(xAxis);
    } else {
      bins = d3.histogram().domain(x.domain()).thresholds(x.ticks(opts.binCount))(values);
      const y = d3.scaleLinear().domain([0, d3.max(bins, d => d.length)]).nice().range([h, 0]);
      svg.selectAll('.bar')
        .data(bins).enter().append('rect').attr('class', 'bar')
        .attr('x', d => x(d.x0) + 1).attr('y', d => y(d.length))
        .attr('width', d => Math.max(0, x(d.x1) - x(d.x0) - 2))
        .attr('height', d => h - y(d.length))
        .attr('fill', theme.barFill);
      const xAxis = d3.axisBottom(x).ticks(4).tickSize(3);
      svg.append('g').attr('class', 'axis axis--x').attr('transform', `translate(0,${h})`).call(xAxis);
    }

    const brush = d3.brushX().extent([[0, 0], [w, h]]).on('brush end', brushed);
    svg.append('g').attr('class', 'brush').call(brush);

    const node = dt.table().node();
    if (!node.id) node.id = 'odc-' + Math.random().toString(36).slice(2);
    const tableId = node.id;
    const rangesForTable = tableRangeState.get(tableId) || [];
    tableRangeState.set(tableId, rangesForTable);

    function brushed(event) {
      const sel = event.selection;
      for (let k = rangesForTable.length - 1; k >= 0; k--) {
        if (rangesForTable[k].colIdx === i) rangesForTable.splice(k, 1);
      }
      if (!sel) { dt.draw(); return; }
      const [x0, x1] = sel;
      const minv = x.invert(x0), maxv = x.invert(x1);
      rangesForTable.push({ colIdx: i, min: minv, max: maxv });
      if (DEFAULTS.debug) {
        console.log('[brushed] tableId=', tableId, 'colIdx=', i, 'min=', minv, 'max=', maxv);
        console.log('[brushed] rangesForTable=', rangesForTable);
      }
      dt.draw();
    }
    container.attr('title', 'Drag to select a numeric range for filtering');
  }

  async function attach(options) {
    const opts = norm(options);
    const $table = $('table[data-module="datatables_view"]').first();
    if (!$table.length) return;
    const d3 = window.d3;
    if (!d3 || !d3.brushX) { console.warn('OdcHistograms: D3 brush not found'); return; }

    if (!$table.hasClass('dataTable') || !$table.data('DataTable')) {
      $table.on('init.dt', () => run($table, opts, d3));
    } else {
      run($table, opts, d3);
    }
  }

  async function run($table, opts, d3) {
    const dt = $table.DataTable ? $table.DataTable() : ($table.dataTable ? $table.dataTable().api() : null);
    if (!dt) return;

    dt.page.len(opts.pageLength).draw(false);
    bindPreXhr($table, opts);

    const resourceId =
      (function () {
        const a = $table.attr('data-resource-url'); const b = window.location.pathname;
        const m1 = a && a.match(/\/resource\/([0-9a-f\-]{36})/i);
        const m2 = b && b.match(/\/resource\/([0-9a-f\-]{36})/i);
        return (m1 && m1[1]) || (m2 && m2[1]) || null;
      })();

    if (opts.ajaxPrefix && resourceId) {
      dt.ajax.url(`${opts.ajaxPrefix}/${resourceId}`).load();
    }

    let total = 0;
    try {
      const info = dt.page.info(); total = info.recordsTotal || 0;
      if (!total && resourceId) total = await (await $.getJSON(
        `${getCkanBaseUrl()}/api/3/action/datastore_search?resource_id=${encodeURIComponent(resourceId)}&limit=0&include_total=true`
      )).result.total;
    } catch (e) { /* ignore */ }

    const cols = dt.columns().indexes().toArray();
    const keys = getColumnKeys(dt);
    const types = getColumnTypes(dt);

    for (const i of cols) {
      const type = types[i];
      const fld = keys[i];
      const isNum = isNumericType(type);

      if (!isNum) {
        if (DEFAULTS.debug) console.log('[skip] col', i, 'key', fld, 'type', type);
        continue;
      }
      if (!fld) {
        if (DEFAULTS.debug) console.warn('[skip] missing field key for col', i);
        continue;
      }

      try {
        let min = null, max = null, counts = null;
        if (opts.serverBins && resourceId) {
          const binsRes = await fetchServerBins(resourceId, fld, opts.binCount);
          if (binsRes && isFinite(binsRes.min) && isFinite(binsRes.max)) {
            min = binsRes.min; max = binsRes.max; counts = binsRes.bins;
          }
        }
        if (min == null || max == null) {
          const values = dt.column(i).data().toArray().map(parseNum).filter(v => v != null && isFinite(v));
          if (!values.length) {
            if (DEFAULTS.debug) console.warn('[skip] no numeric values for col', i, 'key', fld);
            continue;
          }
          min = Math.min.apply(null, values);
          max = Math.max.apply(null, values);
          renderHistogram(dt, i, values, opts, d3, min, max, null);
        } else {
          renderHistogram(dt, i, [], opts, d3, min, max, counts);
        }
      } catch (err) {
        const values = dt.column(i).data().toArray().map(parseNum).filter(v => v != null && isFinite(v));
        if (values.length) {
          const min = Math.min.apply(null, values);
          const max = Math.max.apply(null, values);
          renderHistogram(dt, i, values, opts, d3, min, max, null);
        }
      }
    }

    dt.on('draw', function () {
      const keys2 = getColumnKeys(dt);
      const types2 = getColumnTypes(dt);
      for (const i of cols) {
        const type = types2[i];
        if (!isNumericType(type)) continue;
        const headerRows = dt.table().header().querySelectorAll('tr');
        const filterRow = headerRows[1];
        const fth = filterRow && filterRow.children[i] ? filterRow.children[i] : null;
        if (!fth) continue;
        if (!$(fth).find('.ods-histogram').length) {
          const values = dt.column(i).data().toArray().map(parseNum).filter(v => v != null && isFinite(v));
          if (!values.length) continue;
          const min = Math.min.apply(null, values);
          const max = Math.max.apply(null, values);
          renderHistogram(dt, i, values, opts, d3, min, max, null);
        }
      }
    });
  }

  return { attach };
}));

(function () {
  function boot() {
    window.OdcHistograms && window.OdcHistograms.attach({
      binCount: 24, height: 44,
      ajaxPrefix: '/odc/datatables/ajax', // your Flask route
      debug: true
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
}());
