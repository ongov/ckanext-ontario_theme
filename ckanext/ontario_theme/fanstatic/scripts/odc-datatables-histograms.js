
(function (root, factory) {
  if (typeof define === 'function' && define.amd) define(['jquery'], factory);
  else if (typeof exports === 'object') module.exports = factory(require('jquery'));
  else root.OdcHistograms = factory(root.jQuery);
}(this, function ($) {
  'use strict';

  const DEFAULTS = {
    binCount: 24,
    height: 44,
    margin: { top: 4, right: 8, bottom: 18, left: 8 },
    pageLength: 50,
    smallThreshold: 50,
    serverBins: true,
    ajaxPrefix: null,
    debug: true,
    theme: {
      // Background (full distribution): ODS Secondary Active
      fullFill: 'var(--ontario-colour-secondary-active, #C2E0FF)',
      fullOpacity: 1, //0.65,            // slightly stronger than before
      // Foreground (filtered distribution): ODS darker primary
      filteredFill: 'var(--ontario-colour-primary-darker, #0f3b66)',
      filteredOpacity: 0.95,
      axisColor: 'var(--ontario-colour-ink, #1a1a1a)',
      brushFill: 'rgba(26,90,150,0.18)',
      brushStroke: 'var(--ontario-colour-primary, #1a5a96)'
    }
  };

  // Track table brush ranges: tableId -> [{ colIdx, min, max }, ...]
  const tableRangeState = new Map();

  // Per-table histogram state: domains & per-column overlay updaters
  // tableId -> { domains: {field:{min,max}}, updaters: {colIdx: fn} }
  const histStateByTable = new Map();

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

  // Column keys/types (prefer CKAN data dictionary)
  function getColumnKeys(dt) {
    if (Array.isArray(window.gdataDict) && window.gdataDict.length) {
      return ['_id'].concat(window.gdataDict.map(function (f) { return f.id; }));
    }
    try { return dt.columns().dataSrc().toArray(); } catch (e) { return []; }
  }
  function getColumnTypes(dt) {
    if (Array.isArray(window.gdataDict) && window.gdataDict.length) {
      return ['integer'].concat(window.gdataDict.map(function (f) { return (f.type || '').toLowerCase(); }));
    }
    var types = [], cols = dt.columns().indexes().toArray();
    var headerRows = dt.table().header().querySelectorAll('tr');
    var filterRow = headerRows[1];
    for (var k = 0; k < cols.length; k++) {
      var i = cols[k];
      var th = filterRow && filterRow.children[i] ? filterRow.children[i] : null;
      types.push(((th && th.getAttribute('data-type')) || '').toLowerCase());
    }
    if (types.length && !types[0]) types[0] = 'integer';
    return types;
  }
  function isNumericType(t) {
    t = (t || '').toLowerCase();
    return /^(?:int|integer|int2|int4|int8|smallint|bigint|float|float4|float8|real|double(?:\s+precision)?|numeric|decimal|number)$/.test(t);
  }
  function isIntegerType(t) {
    t = (t || '').toLowerCase();
    return /^(?:int|integer|int2|int4|int8|smallint|bigint)$/.test(t);
  }
  // Histogram eligible = numeric AND not "_id"
  function isHistogramEligible(field, type) {
    return field && field !== '_id' && isNumericType(type);
  }

  // Send ranges & histogram params on every request
  function bindPreXhr($table, opts) {
    $table.off('preXhr.dt.odc').on('preXhr.dt.odc', function (e, settings, data) {
      var dt = $(settings.nTable).DataTable();
      var node = dt.table().node();
      if (!node.id) node.id = 'odc-' + Math.random().toString(36).slice(2);
      var tableId = node.id;

      var keys = getColumnKeys(dt);
      var types = getColumnTypes(dt);

      var rangesForTable = tableRangeState.get(tableId) || [];
      var ranges = rangesForTable.map(function (r) {
        var field = keys[r.colIdx];
        var type = types[r.colIdx];
        if (!isHistogramEligible(field, type)) return null;
        var min = r.min, max = r.max;
        if (isIntegerType(type)) { min = Math.floor(min); max = Math.ceil(max); }
        return { field: field, colIndex: r.colIdx, min: min, max: max };
      }).filter(function (rr) { return rr && rr.field && isFinite(rr.min) && isFinite(rr.max); });

      data.odcRanges = JSON.stringify(ranges);
      data.columnNames = JSON.stringify(keys);

      var numericFields = keys.filter(function (k, i) { return isHistogramEligible(k, types[i]); });
      data.odcHist = '1';
      data.odcBinCount = String(opts.binCount);
      data.odcHistFields = JSON.stringify(numericFields);

      var hs = histStateByTable.get(tableId);
      var domains = (hs && hs.domains) ? hs.domains : {};
      // Filter domains to eligible fields
      var domainsFiltered = {};
      Object.keys(domains || {}).forEach(function (k) {
        var idx = keys.indexOf(k);
        var t = (idx >= 0) ? types[idx] : '';
        if (isHistogramEligible(k, t)) domainsFiltered[k] = domains[k];
      });
      data.odcHistDomain = JSON.stringify(domainsFiltered);

      if (opts.debug) {
        console.log('[preXhr] tableId=', tableId);
        console.log('[preXhr] keys=', keys);
        console.log('[preXhr] rangesForTable=', rangesForTable);
        console.log('[preXhr] odcRanges=', ranges);
        console.log('[preXhr] odcHistFields=', numericFields);
        console.log('[preXhr] odcHistDomain=', domainsFiltered);
      }
    });
  }

  // Fetch full-distribution bins (background layer) — skip _id
  async function fetchServerBins(resourceId, field, bins) {
    if (field === '_id') return null;
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
      const data = rows.map(function (r) { return { bin: Number(r.bin), count: Number(r.count) }; });
      return { min: minv, max: maxv, bins: data, binCount: bins };
    }
    return null;
  }

  // Draw a dual-layer histogram (full background + filtered overlay)
  function renderHistogram(dt, i, values, opts, d3, min, max, countsFromServer) {
    const theme = opts.theme;

    const headerRows = dt.table().header().querySelectorAll('tr');
    const filterRow = headerRows[1];
    const fth = filterRow && filterRow.children[i] ? filterRow.children[i] : null;
    if (!fth) return;

    const th = $(fth);
    th.addClass('odc-numeric-filter').empty();

    const w = (function () { const rect = fth.getBoundingClientRect(); return Math.max(140, Math.floor(rect.width)); }()) - opts.margin.left - opts.margin.right;
    const h = opts.height - opts.margin.top - opts.margin.bottom;

    const container = $('<div class="ods-histogram" aria-label="Histogram filter"></div>');
    const svgEl = $('<svg class="ods-histogram-svg" role="img"></svg>')
      .attr('width', w + opts.margin.left + opts.margin.right)
      .attr('height', h + opts.margin.top + opts.margin.bottom);
    container.append(svgEl);
    th.append(container);

    const svg = d3.select(svgEl[0]).append('g')
      .attr('transform', `translate(${opts.margin.left},${opts.margin.top})`);

    const x = d3.scaleLinear().domain([min, max]).range([0, w]);
    const types = getColumnTypes(dt);
    const keys = getColumnKeys(dt);
    const field = keys[i];
    const isInt = isIntegerType(types[i]);

    // Layers
    const gFull = svg.append('g').attr('class', 'layer-full');
    const gSel  = svg.append('g').attr('class', 'layer-filtered')
      .style('mix-blend-mode', 'multiply'); // tint effect over background

    let yFullMax = 0;

    if (countsFromServer) {
      const bw = (max - min) / opts.binCount;
      yFullMax = d3.max(countsFromServer, function (row) { return row.count; }) || 0;
      const y = d3.scaleLinear().domain([0, yFullMax]).nice().range([h, 0]);

      gFull.selectAll('rect.bar-full')
        .data(countsFromServer).enter().append('rect')
        .attr('class', 'bar-full')
        .attr('x', function (row) { return x(min + (row.bin - 1) * bw) + 1; })
        .attr('y', function (row) { return y(row.count); })
        .attr('width', function (row) { return Math.max(0, x(min + row.bin * bw) - x(min + (row.bin - 1) * bw) - 2); })
        .attr('height', function (row) { return h - y(row.count); })
        // Use inline style for fill to defeat external CSS overrides
        .style('fill', theme.fullFill)
        .style('opacity', theme.fullOpacity);

      const xAxis = d3.axisBottom(x)
        .ticks(isInt ? Math.min(6, Math.max(1, Math.round(max - min))) : 4)
        .tickSize(3)
        .tickFormat(isInt ? d3.format('d') : undefined);
      svg.append('g').attr('class', 'axis axis--x').attr('transform', `translate(0,${h})`).call(xAxis);
    } else {
      const bins = d3.histogram().domain(x.domain()).thresholds(x.ticks(opts.binCount))(values);
      yFullMax = d3.max(bins, function (row) { return row.length; }) || 0;
      const y = d3.scaleLinear().domain([0, yFullMax]).nice().range([h, 0]);

      gFull.selectAll('rect.bar-full')
        .data(bins).enter().append('rect')
        .attr('class', 'bar-full')
        .attr('x', function (row) { return x(row.x0) + 1; })
        .attr('y', function (row) { return y(row.length); })
        .attr('width', function (row) { return Math.max(0, x(row.x1) - x(row.x0) - 2); })
        .attr('height', function (row) { return h - y(row.length); })
        .style('fill', theme.fullFill)      // inline style
        .style('opacity', theme.fullOpacity);

      const xAxis = d3.axisBottom(x)
        .ticks(isInt ? Math.min(6, Math.max(1, Math.round(max - min))) : 4)
        .tickSize(3)
        .tickFormat(isInt ? d3.format('d') : undefined);
      svg.append('g').attr('class', 'axis axis--x').attr('transform', `translate(0,${h})`).call(xAxis);
    }

    // Brush (no brush on _id)
    const enableBrush = (field !== '_id');
    if (enableBrush) {
      const brush = d3.brushX().extent([[0, 0], [w, h]]).on('brush end', brushed);
      svg.append('g').attr('class', 'brush').call(brush);
    }

    // Table state
    const node = dt.table().node();
    if (!node.id) node.id = 'odc-' + Math.random().toString(36).slice(2);
    const tableId = node.id;
    const rangesForTable = tableRangeState.get(tableId) || [];
    tableRangeState.set(tableId, rangesForTable);

    // --- updater for filtered overlay (tints matching bins) ---
    const bw = (max - min) / opts.binCount;
    const yForSel = d3.scaleLinear().domain([0, yFullMax]).nice().range([h, 0]); // lock to full max

    function updateFilteredLayer(binCounts) {
      if (!Array.isArray(binCounts)) binCounts = [];
      const bars = gSel.selectAll('rect.bar-overlay').data(binCounts, function (row) {
        return (row && typeof row.bin !== 'undefined') ? row.bin : -1;
      });

      bars.enter().append('rect')
        .attr('class', 'bar-overlay')
        .attr('x', function (row) { return x(min + (row.bin - 1) * bw) + 1; })
        .attr('width', function (row) { return Math.max(0, x(min + row.bin * bw) - x(min + (row.bin - 1) * bw) - 2); })
        .style('fill', theme.filteredFill)       // inline style
        .style('opacity', theme.filteredOpacity)
        .style('pointer-events', 'none') // never block brushing
        .merge(bars)
        .attr('y', function (row) { return yForSel(row.count || 0); })
        .attr('height', function (row) { return h - yForSel(row.count || 0); });

      bars.exit().remove();
    }

    // store updater and domain for server to reuse — skip _id
    const hs = histStateByTable.get(tableId) || { domains: {}, updaters: {} };
    if (field !== '_id') {
      hs.domains[field] = { min: min, max: max };
      hs.updaters[i] = updateFilteredLayer;
    }
    histStateByTable.set(tableId, hs);

    function brushed(event) {
      const sel = event.selection;
      for (let k = rangesForTable.length - 1; k >= 0; k--) {
        if (rangesForTable[k].colIdx === i) rangesForTable.splice(k, 1);
      }
      if (!sel) { dt.draw(); return; }
      const x0 = sel[0], x1 = sel[1];
      let minv = x.invert(x0), maxv = x.invert(x1);
      if (isInt) {
        minv = Math.floor(minv);
        maxv = Math.ceil(maxv);
        if (maxv < minv) { const t = minv; minv = maxv; maxv = t; }
      }
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
      $table.on('init.dt', function () { run($table, opts, d3); });
    } else {
      run($table, opts, d3);
    }
  }

  async function run($table, opts, d3) {
    const dt = $table.DataTable ? $table.DataTable() : ($table.dataTable ? $table.dataTable().api() : null);
    if (!dt) return;

    dt.page.len(opts.pageLength).draw(false);
    bindPreXhr($table, opts);

    const resourceId = (function () {
      const a = $table.attr('data-resource-url'); const b = window.location.pathname;
      const m1 = a && a.match(/\/resource\/([0-9a-f\-]{36})/i);
      const m2 = b && b.match(/\/resource\/([0-9a-f\-]{36})/i);
      return (m1 && m1[1]) || (m2 && m2[1]) || null;
    }());

    if (opts.ajaxPrefix && resourceId) {
      dt.ajax.url(`${opts.ajaxPrefix}/${resourceId}`).load();
    }

    const cols = dt.columns().indexes().toArray();
    const keys = getColumnKeys(dt);
    const types = getColumnTypes(dt);

    // Initial render per eligible numeric column (exclude _id)
    for (const i of cols) {
      const type = types[i];
      const fld = keys[i];
      const isEligible = isHistogramEligible(fld, type);
      if (!isEligible) { if (DEFAULTS.debug) console.log('[skip] col', i, 'key', fld, 'type', type); continue; }
      if (!fld) { if (DEFAULTS.debug) console.warn('[skip] missing field key for col', i); continue; }

      try {
        let min = null, max = null, counts = null;
        if (opts.serverBins && resourceId) {
          const binsRes = await fetchServerBins(resourceId, fld, opts.binCount);
          if (binsRes && isFinite(binsRes.min) && isFinite(binsRes.max)) {
            min = binsRes.min; max = binsRes.max; counts = binsRes.bins;
          }
        }
        if (min == null || max == null) {
          const values = dt.column(i).data().toArray().map(parseNum).filter(function (v) { return v != null && isFinite(v); });
          if (!values.length) { if (DEFAULTS.debug) console.warn('[skip] no numeric values for col', i, 'key', fld); continue; }
          min = Math.min.apply(null, values);
          max = Math.max.apply(null, values);
          renderHistogram(dt, i, values, opts, d3, min, max, null);
        } else {
          renderHistogram(dt, i, [], opts, d3, min, max, counts);
        }
      } catch (err) {
        const values = dt.column(i).data().toArray().map(parseNum).filter(function (v) { return v != null && isFinite(v); });
        if (values.length) {
          const min = Math.min.apply(null, values);
          const max = Math.max.apply(null, values);
          renderHistogram(dt, i, values, opts, d3, min, max, null);
        }
      }
    }

    // Update overlays for ALL eligible numeric columns on each server draw
    dt.off('xhr.dt.odc').on('xhr.dt.odc', function (e, settings, json) {
      try {
        const node = dt.table().node();
        const tableId = node.id || '';
        const hs = histStateByTable.get(tableId);
        if (!hs || !json || !json.histograms) return;
        const keys2 = getColumnKeys(dt);
        const types2 = getColumnTypes(dt);
        const cols2 = dt.columns().indexes().toArray();
        for (const i of cols2) {
          const fld = keys2[i];
          const type = types2[i];
          if (!isHistogramEligible(fld, type)) continue;
          const h = json.histograms[fld];
          if (!h || !Array.isArray(h.bins)) continue;
          const updater = hs.updaters[i];
          if (typeof updater === 'function') updater(h.bins);
        }
      } catch (err) {
        if (DEFAULTS.debug) console.warn('[xhr.odc] histogram update failed:', err);
      }
    });
  }

  return { attach };
}));

// Auto-boot
(function () {
  function boot() {
    window.OdcHistograms && window.OdcHistograms.attach({
      binCount: 24,
      height: 44,
      ajaxPrefix: '/odc/datatables/ajax', // Flask route
      debug: true,
      theme: {
        fullFill: 'var(--ontario-colour-secondary-active, #C2E0FF)',  // << updated
        filteredFill: 'var(--ontario-colour-primary-darker, #0f3b66)'
      }
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
}());
