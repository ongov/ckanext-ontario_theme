
/**
 * odc-datatables-histograms.js
 * Brushable histograms for CKAN 2.11 datatables_view (server-side processing).
 *
 * - Renders D3 brushable histograms in the filter row (second <thead> row) for numeric columns.
 * - Sends brush ranges (+ column names) on each Ajax request via preXhr.dt (server applies WHERE).
 * - Sets DataTables page length to 50 at runtime (no re-init).
 * - Uses CKAN datastore_search_sql + PostgreSQL width_bucket(...) for aggregated server-side bins.
 *
 * Docs:
 *  - DataTables page length API (.page.len()) / pageLength option                    https://datatables.net/reference/api/page.len()        [2](https://docs.ckan.org/en/2.9/maintaining/datastore.html)
 *  - DataTables preXhr.dt (augment request before Ajax)                              https://datatables.net/reference/event/preXhr         
 *  - DataTables ajax.url().load() (switch data source at runtime)                    https://datatables.net/reference/api/ajax.url()       
 *  - CKAN DataStore SQL + width_bucket                                               https://docs.ckan.org/en/2.9/maintaining/datastore.html  [1](https://docs.ckan.org/en/2.11/maintaining/datastore.html)
 */

(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define(['jquery'], factory);
  } else if (typeof exports === 'object') {
    module.exports = factory(require('jquery'));
  } else {
    root.OdcHistograms = factory(root.jQuery);
  }
}(this, function ($) {
  'use strict';

  // ---------------- Configuration ----------------
  const DEFAULTS = {
    binCount: 24,
    height: 44,
    margin: { top: 4, right: 8, bottom: 18, left: 8 },
    pageLength: 50,
    smallThreshold: 50,          // if total rows <= this, we can fetch all values (optional)
    serverBins: true,            // use width_bucket bins via datastore_search_sql when possible
    ajaxPrefix: null,            // OPTIONAL: set to '/odc/datatables/ajax' to point to your route
    theme: {
      barFill: 'var(--ontario-colour-primary, #1a5a96)',
      barFillInactive: 'var(--ontario-colour-secondary, #8a8a8a)',
      axisColor: 'var(--ontario-colour-ink, #1a1a1a)',
      brushFill: 'rgba(26, 90, 150, 0.18)',
      brushStroke: 'var(--ontario-colour-primary, #1a5a96)'
    }
  };

  // ---------------- Option normalizer (deep merge for theme) ----------------
  function normalizeOptions(userOpts) {
    const base = Object.assign({}, DEFAULTS, userOpts || {});
    base.theme = Object.assign({}, DEFAULTS.theme, (userOpts && userOpts.theme) || {});
    // Ensure margin exists even if a partial margin was passed
    base.margin = Object.assign({}, DEFAULTS.margin, (userOpts && userOpts.margin) || {});
    return base;
  }

  // ---------------- Helpers ----------------
  function extractResourceIdFromUrl(urlOrPath) {
    if (!urlOrPath) return null;
    const m = String(urlOrPath).match(/\/resource\/([0-9a-f-]{36})/i);
    return m ? m[1] : null;
  }
  function getCkanBaseUrl() { return window.location.origin; }

  const utils = {
    parseNumber: function (v) {
      if (v == null) return null;
      if (typeof v === 'number' && isFinite(v)) return v;
      const s = String(v).trim(); if (!s) return null;
      const rangeMatch = s.match(/^(-?\d[\d,\.]*)\s*[-–—]\s*(-?\d[\d,\.]*)$/);
      if (rangeMatch) {
        const a = utils.parseNumber(rangeMatch[1]); const b = utils.parseNumber(rangeMatch[2]);
        if (a != null && b != null) return (a + b) / 2;
      }
      const cleaned = s.replace(/[%,$€£\s]/g, '').replace(/,/g, '');
      const num = parseFloat(cleaned);
      return isNaN(num) ? null : num;
    }
  };

  // ---------------- Styles (ODS-friendly) ----------------
  let stylesInjected = false;
  function injectStyles() {
    if (stylesInjected) return; stylesInjected = true;
    const css = `
      .ods-histogram { display:flex; align-items:center; gap:8px; padding:6px 8px; border-radius:4px; }
      .ods-histogram .ods-histogram-svg { display:block; width:100%; height:auto; }
      .ods-histogram .bar { shape-rendering:crispEdges; }
      .ods-histogram .axis text { fill: var(--ontario-colour-ink, #1a1a1a); font-size: 11px; }
      .ods-histogram .selection { fill: rgba(26,90,150,0.18); stroke: var(--ontario-colour-primary, #1a5a96); }
      thead tr:nth-child(2) th.odc-numeric-filter input[type="search"] { display: none !important; }
    `;
    const tag = document.createElement('style'); tag.type = 'text/css';
    tag.appendChild(document.createTextNode(css)); document.head.appendChild(tag);
  }

  // ---------------- DataTables header helpers ----------------
  function headerRows(dt) { return dt.table().header().querySelectorAll('tr'); }
  function titleTh(dt, i) { const r = headerRows(dt)[0]; return r && r.children[i] ? r.children[i] : dt.column(i).header(); }
  function filterTh(dt, i) { const r = headerRows(dt)[1]; return r && r.children[i] ? r.children[i] : null; }
  function fieldName(dt, i) { const th = titleTh(dt, i); return th ? th.getAttribute('data-name') || null : null; }
  function filterWidth(dt, i) { const th = filterTh(dt, i) || titleTh(dt, i); const rect = th.getBoundingClientRect(); return Math.max(140, Math.floor(rect.width)); }

  // ---------------- Range state ----------------
  const tableRangeState = new Map();

  // ---------------- Ajax hook: send brush ranges + column names ----------------
  function bindPreXhrHook($table) {
    $table.off('preXhr.dt.odc').on('preXhr.dt.odc', function (e, settings, data) {
      const dt = $(settings.nTable).DataTable();
      const tableId = settings.nTable && settings.nTable.id ? settings.nTable.id : null;

      // Active brush ranges
      const ranges = (tableRangeState.get(tableId) || []).map(r => ({
        field: fieldName(dt, r.colIdx),
        colIndex: r.colIdx,
        min: r.min,
        max: r.max
      }));
      data.odcRanges = ranges;

      // Column names from TITLE row (data-name="...")
      const titleRow = dt.table().header().querySelectorAll('tr')[0];
      const names = dt.columns().indexes().toArray().map(i => {
        const th = titleRow && titleRow.children[i] ? titleRow.children[i] : null;
        return th ? th.getAttribute('data-name') : null;
      });
      data.columnNames = JSON.stringify(names);
    });
  }

  // ---------------- CKAN API: totals / values / server bins ----------------
  async function fetchTotal(resourceId) {
    const url = `${getCkanBaseUrl()}/api/3/action/datastore_search?resource_id=${encodeURIComponent(resourceId)}&limit=0&include_total=true`;
    const res = await $.getJSON(url);
    if (res && res.success && res.result) return res.result.total || 0;
    return 0;
  }
  async function fetchAllColumnValues(resourceId, fieldName) {
    const url = `${getCkanBaseUrl()}/api/3/action/datastore_search?resource_id=${encodeURIComponent(resourceId)}&fields=${encodeURIComponent(fieldName)}&limit=50000`;
    const res = await $.getJSON(url);
    if (res && res.success && res.result && res.result.records) {
      return res.result.records.map(r => utils.parseNumber(r[fieldName])).filter(v => v != null && isFinite(v));
    }
    return [];
  }
  async function fetchServerBins(resourceId, field, bins) {
    const identRes = `"${resourceId.replace(/"/g, '""')}"`;
    const identFld = `"${field.replace(/"/g, '""')}"`;
    const sql =
      `WITH mm AS (SELECT MIN(${identFld}) AS minv, MAX(${identFld}) AS maxv FROM ${identRes} WHERE ${identFld} IS NOT NULL)
       SELECT width_bucket(${identFld}, (SELECT minv FROM mm), (SELECT maxv FROM mm), ${bins}) AS bin,
              COUNT(*) AS count,
              (SELECT minv FROM mm) AS minv,
              (SELECT maxv FROM mm) AS maxv
       FROM ${identRes}
       WHERE ${identFld} IS NOT NULL
       GROUP BY bin
       ORDER BY bin`;
    const url = `${getCkanBaseUrl()}/api/3/action/datastore_search_sql?sql=${encodeURIComponent(sql)}`;
    const res = await $.getJSON(url);
    if (res && res.success && res.result && res.result.records) {
      const rows = res.result.records;
      const minv = rows.length ? Number(rows[0].minv) : 0;
      const maxv = rows.length ? Number(rows[0].maxv) : 1;
      const data = rows.map(r => ({ bin: Number(r.bin), count: Number(r.count) }));
      return { min: minv, max: maxv, bins: data, binCount: bins };
    }
    return { min: 0, max: 1, bins: [], binCount: bins };
  }

  // ---------------- Rendering (filter row) ----------------
  function renderHistogramFromValues(dt, i, values, options, d3) {
    const opts = normalizeOptions(options);
    const theme = opts.theme;

    const w = filterWidth(dt, i) - opts.margin.left - opts.margin.right;
    const h = opts.height - opts.margin.top - opts.margin.bottom;
    const th = $(filterTh(dt, i)); if (!th.length) return;

    th.addClass('odc-numeric-filter').empty();
    const container = $('<div class="ods-histogram" aria-label="Histogram filter"></div>');
    const svgEl = $('<svg class="ods-histogram-svg" role="img"></svg>')
      .attr('width', w + opts.margin.left + opts.margin.right)
      .attr('height', h + opts.margin.top + opts.margin.bottom);
    container.append(svgEl); th.append(container);

    const svg = d3.select(svgEl[0]).append('g')
      .attr('transform', `translate(${opts.margin.left},${opts.margin.top})`);
    const min = d3.min(values), max = d3.max(values);
    const x = d3.scaleLinear().domain([min, max]).range([0, w]);
    const bins = d3.histogram().domain(x.domain()).thresholds(x.ticks(opts.binCount))(values);
    const y = d3.scaleLinear().domain([0, d3.max(bins, d => d.length)]).nice().range([h, 0]);

    svg.selectAll('.bar')
      .data(bins).enter().append('rect').attr('class', 'bar')
      .attr('x', d => x(d.x0) + 1).attr('y', d => y(d.length))
      .attr('width', d => Math.max(0, x(d.x1) - x(d.x0) - 2))
      .attr('height', d => h - y(d.length))
      .attr('fill', theme.barFill);

    const xAxis = d3.axisBottom(x).ticks(4).tickSize(3);
    svg.append('g').attr('class', 'axis axis--x').attr('transform', `translate(0,${h})`).call(xAxis);

    const brush = d3.brushX().extent([[0, 0], [w, h]]).on('brush end', brushed);
    svg.append('g').attr('class', 'brush').call(brush);

    const tableId = dt.table().node().id || (dt.table().node().id = 'odc-' + Math.random().toString(36).slice(2));
    const parser = utils.parseNumber;
    const rangesForTable = tableRangeState.get(tableId) || [];
    tableRangeState.set(tableId, rangesForTable);

    function brushed(event) {
      const sel = event.selection;
      const key = i;
      for (let k = rangesForTable.length - 1; k >= 0; k--) {
        if (rangesForTable[k].colIdx === key) rangesForTable.splice(k, 1);
      }
      if (!sel) { dt.draw(); return; }
      const [x0, x1] = sel;
      rangesForTable.push({ colIdx: key, min: x.invert(x0), max: x.invert(x1), parser });
      dt.draw(); // server-side redraw; preXhr.dt will include odcRanges
    }
    container.attr('title', 'Drag to select a numeric range for filtering');
  }

  function renderHistogramFromServer(dt, i, binResult, options, d3) {
    const opts = normalizeOptions(options);
    const theme = opts.theme;

    const w = filterWidth(dt, i) - opts.margin.left - opts.margin.right;
    const h = opts.height - opts.margin.top - opts.margin.bottom;
    const th = $(filterTh(dt, i)); if (!th.length) return;

    th.addClass('odc-numeric-filter').empty();
    const container = $('<div class="ods-histogram" aria-label="Histogram filter"></div>');
    const svgEl = $('<svg class="ods-histogram-svg" role="img"></svg>')
      .attr('width', w + opts.margin.left + opts.margin.right)
      .attr('height', h + opts.margin.top + opts.margin.bottom);
    container.append(svgEl); th.append(container);

    const svg = d3.select(svgEl[0]).append('g')
      .attr('transform', `translate(${opts.margin.left},${opts.margin.top})`);
    const min = binResult.min, max = binResult.max, bins = binResult.bins;
    const x = d3.scaleLinear().domain([min, max]).range([0, w]);
    const y = d3.scaleLinear().domain([0, d3.max(bins, d => d.count)]).nice().range([h, 0]);
    const binWidth = (max - min) / ((options && options.binCount) || DEFAULTS.binCount);

    svg.selectAll('.bar')
      .data(bins).enter().append('rect').attr('class', 'bar')
      .attr('x', d => x(min + (d.bin - 1) * binWidth) + 1)
      .attr('y', d => y(d.count))
      .attr('width', Math.max(0, x(min + d.bin * binWidth) - x(min + (d.bin - 1) * binWidth) - 2))
      .attr('height', d => h - y(d.count))
      .attr('fill', theme.barFill);

    const xAxis = d3.axisBottom(x).ticks(4).tickSize(3);
    svg.append('g').attr('class', 'axis axis--x').attr('transform', `translate(0,${h})`).call(xAxis);

    const brush = d3.brushX().extent([[0, 0], [w, h]]).on('brush end', brushed);
    svg.append('g').attr('class', 'brush').call(brush);

    const tableId = dt.table().node().id || (dt.table().node().id = 'odc-' + Math.random().toString(36).slice(2));
    const parser = utils.parseNumber;
    const rangesForTable = tableRangeState.get(tableId) || [];
    tableRangeState.set(tableId, rangesForTable);

    function brushed(event) {
      const sel = event.selection;
      const key = i;
      for (let k = rangesForTable.length - 1; k >= 0; k--) {
        if (rangesForTable[k].colIdx === key) rangesForTable.splice(k, 1);
      }
      if (!sel) { dt.draw(); return; }
      const [x0, x1] = sel;
      rangesForTable.push({ colIdx: key, min: x.invert(x0), max: x.invert(x1), parser });
      dt.draw(); // server applies the filter via odcRanges
    }
    container.attr('title', 'Drag to select a numeric range for filtering');
  }

  // ---------------- Orchestration ----------------
  async function attach(options) {
    injectStyles();

    const $table = $('table[data-module="datatables_view"]').first();
    if (!$table.length) return;

    const d3 = window.d3;
    if (!d3 || !d3.brushX) { console.warn('OdcHistograms: D3 brush not found'); return; }  // needs d3-brush

    // Wait for DataTables init
    if (!$table.hasClass('dataTable') || !$table.data('DataTable')) {
      $table.on('init.dt', () => run($table, options, d3));
    } else {
      run($table, options, d3);
    }
  }

  async function run($table, options, d3) {
    const opts = normalizeOptions(options);
    const dt = $table.DataTable ? $table.DataTable() : ($table.dataTable ? $table.dataTable().api() : null);
    if (!dt) return;

    // Set page length to 50 (runtime API)                                                 // DataTables API [2](https://docs.ckan.org/en/2.9/maintaining/datastore.html)
    dt.page.len(opts.pageLength).draw(false);

    // Send brush ranges on every Ajax call
    bindPreXhrHook($table);

    // OPTIONAL: point Ajax at your route that honors odcRanges
    const resourceId =
      extractResourceIdFromUrl($table.attr('data-resource-url')) ||
      extractResourceIdFromUrl(window.location.pathname);
    if (opts.ajaxPrefix && resourceId) {
      dt.ajax.url(`${opts.ajaxPrefix}/${resourceId}`).load();                             // ajax.url().load() 
    }

    // Determine total rows to choose bin strategy
    let total = 0;
    try {
      const info = dt.page.info(); // recordsTotal in server-side mode                    // DataTables page.info() docs
      total = info.recordsTotal || 0;
      if (!total && resourceId) total = await fetchTotal(resourceId);
    } catch (e) {}

    // Render histograms per numeric column in filter row
    const cols = dt.columns().indexes().toArray();
    for (const i of cols) {
      const fth = filterTh(dt, i); if (!fth) continue;
      const dtype = fth.getAttribute('data-type') || '';
      const isNumeric = /^int|^float|^number|^numeric/i.test(dtype);
      if (!isNumeric) continue;

      const fld = fieldName(dt, i);
      if (!fld) continue;

      try {
        if (opts.serverBins && resourceId) {
          // Prefer server-side aggregate bins
          const bins = await fetchServerBins(resourceId, fld, opts.binCount);
          renderHistogramFromServer(dt, i, bins, opts, d3);
        } else if (total && total <= opts.smallThreshold && resourceId) {
          // Small dataset: fetch all values once for accurate bins
          const values = await fetchAllColumnValues(resourceId, fld);
          if (values.length) renderHistogramFromValues(dt, i, values, opts, d3);
        } else {
          // Fallback: current page values
          const values = dt.column(i).data().toArray()
            .map(utils.parseNumber).filter(v => v != null && isFinite(v));
          if (values.length) renderHistogramFromValues(dt, i, values, opts, d3);
        }
      } catch (err) {
        const values = dt.column(i).data().toArray()
          .map(utils.parseNumber).filter(v => v != null && isFinite(v));
        if (values.length) renderHistogramFromValues(dt, i, values, opts, d3);
      }
    }

    // Rebuild histograms on header redraws
    dt.on('draw', function () {
      for (const i of cols) {
        const th = filterTh(dt, i); if (!th) continue;
        if (!$(th).find('.ods-histogram').length) {
          const dtype = th.getAttribute('data-type') || '';
          const isNumeric = /^int|^float|^number|^numeric/i.test(dtype);
          if (!isNumeric) continue;
          const values = dt.column(i).data().toArray()
            .map(utils.parseNumber).filter(v => v != null && isFinite(v));
          if (values.length) renderHistogramFromValues(dt, i, values, opts, d3);
        }
      }
    });
  }

  // Public API
  return { attach };
}));

// Auto-init
(function () {
  function boot() {
    // If you want to change the ajax endpoint at runtime, set ajaxPrefix here:
    // e.g., { ajaxPrefix: '/odc/datatables/ajax' }
    window.OdcHistograms && window.OdcHistograms.attach({
      binCount: 24,
      height: 44
      // , ajaxPrefix: '/odc/datatables/ajax'
      // , theme: { brushFill: 'rgba(26,90,150,0.12)' } // partial overrides are safe now
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
