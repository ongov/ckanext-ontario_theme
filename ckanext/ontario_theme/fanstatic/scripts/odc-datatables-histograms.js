
/**
 * odc-datatables-histogram.js
 * Brushable histograms in CKAN 2.11 DataTables column FILTER row (Ontario Design System-friendly).
 *
 * This version draws the histogram in the second <thead> row (the filter controls),
 * replacing the default text input for numeric columns.
 *
 * Dependencies:
 *   - jQuery
 *   - DataTables (CKAN datatables_view)
 *   - D3 v5+ (for d3.brushX)
 *
 * Export: window.OdcHistogram = { init, attach, utils }
 */

(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define(['jquery'], factory);
  } else if (typeof exports === 'object') {
    module.exports = factory(require('jquery'));
  } else {
    root.OdcHistogram = factory(root.jQuery);
  }
}(this, function ($) {
  'use strict';

  // ---- ODS-friendly defaults
  const DEFAULTS = {
    binCount: 20,
    height: 44,
    margin: { top: 4, right: 8, bottom: 18, left: 8 },
    theme: {
      barFill: 'var(--ontario-colour-primary, #1a5a96)',
      barFillInactive: 'var(--ontario-colour-secondary, #8a8a8a)',
      axisColor: 'var(--ontario-colour-ink, #1a1a1a)',
      brushFill: 'rgba(26, 90, 150, 0.18)',
      brushStroke: 'var(--ontario-colour-primary, #1a5a96)'
    }
  };

  // ---- Helpers --------------------------------------------------------------
  function extractResourceIdFromUrl(url) {
    if (!url) return null;
    var m = String(url).match(/\/resource\/([0-9a-f-]{36})/i);
    return m ? m[1] : null;
  }

  const utils = {
    parseNumber: function (v) {
      if (v == null) return null;
      if (typeof v === 'number' && isFinite(v)) return v;
      const s = String(v).trim();
      if (!s) return null;
      const rangeMatch = s.match(/^(-?\d[\d,\.]*)\s*[-–—]\s*(-?\d[\d,\.]*)$/);
      if (rangeMatch) {
        const a = utils.parseNumber(rangeMatch[1]);
        const b = utils.parseNumber(rangeMatch[2]);
        if (a != null && b != null) return (a + b) / 2;
      }
      const cleaned = s.replace(/[%,$€£\s]/g, '').replace(/,/g, '');
      const num = parseFloat(cleaned);
      return isNaN(num) ? null : num;
    },
    isNumericColumn: function (dt, colIdx) {
      // sample a small subset
      const sample = dt.column(colIdx).data().toArray().slice(0, 50);
      let numericCount = 0;
      for (let i = 0; i < sample.length; i++) {
        if (utils.parseNumber(sample[i]) !== null) numericCount++;
      }
      return numericCount >= Math.max(5, Math.ceil(sample.length * 0.3));
    }
  };

  // ---- Wait for libs --------------------------------------------------------
  function waitForD3(maxMs = 5000) {
    return new Promise((resolve, reject) => {
      const start = Date.now();
      (function check() {
        if (window.d3 && window.d3.brushX) return resolve(window.d3);
        if (Date.now() - start > maxMs) return reject(new Error('D3 not found'));
        setTimeout(check, 50);
      })();
    });
  }

  function waitForDataTables(maxMs = 8000) {
    return new Promise((resolve, reject) => {
      const start = Date.now();
      (function check() {
        const has = !!($.fn && ($.fn.DataTable || $.fn.dataTable));
        if (has) return resolve();
        if (Date.now() - start > maxMs) return reject(new Error('DataTables not found'));
        setTimeout(check, 50);
      })();
    });
  }

  // ---- Global DT filter and per-table ranges --------------------------------
  const tableRangeState = new Map();
  let globalSearchRegistered = false;

  function registerGlobalRangeFilterOnce() {
    if (globalSearchRegistered) return;
    if (!$.fn || !$.fn.dataTable || !$.fn.dataTable.ext || !$.fn.dataTable.ext.search) return;
    // Custom range filter in DataTables search pipeline. [1](https://datatables.net/forums/discussion/51688/how-can-i-have-select-inputs-in-second-row-of-table-header)[2](https://www.geeksforgeeks.org/jquery/how-to-handle-multiple-rows-selection-using-jquery-datatables-plugin/)
    $.fn.dataTable.ext.search.push(function (settings, data) {
      const tableId = settings.nTable && settings.nTable.id ? settings.nTable.id : null;
      const ranges = tableRangeState.get(tableId);
      if (!ranges || ranges.length === 0) return true;
      for (let i = 0; i < ranges.length; i++) {
        const r = ranges[i];
        const raw = data[r.colIdx];
        const value = r.parser(raw);
        if (value === null) return false;
        if (value < r.min || value > r.max) return false;
      }
      return true;
    });
    globalSearchRegistered = true;
  }

  // ---- Styles ---------------------------------------------------------------
  let stylesInjected = false;
  function injectStyles() {
    if (stylesInjected) return;
    stylesInjected = true;
    const css = `
      /* Histogram widget that fits ODS typography/colour tokens */
      .ods-histogram { display:flex; align-items:center; gap:8px; padding:6px 8px; border-radius:4px; }
      .ods-histogram .ods-histogram-svg { display:block; width:100%; height:auto; }
      .ods-histogram .bar { shape-rendering:crispEdges; }
      .ods-histogram .axis text { fill: var(--ontario-colour-ink, #1a1a1a); font-size: 11px; }
      .ods-histogram .selection { fill: rgba(26,90,150,0.18); stroke: var(--ontario-colour-primary, #1a5a96); }
      /* Optional: hide default text input when we replace it */
      thead tr:nth-child(2) th.odc-numeric-filter input[type="search"] { display: none !important; }
    `;
    const tag = document.createElement('style');
    tag.type = 'text/css';
    tag.appendChild(document.createTextNode(css));
    document.head.appendChild(tag);
  }

  // ---- Header accessors -----------------------------------------------------
  function getTitleTh(dt, colIdx) {
    const headerRows = dt.table().header().querySelectorAll('tr');
    const titleRow = headerRows[0];
    return titleRow && titleRow.children[colIdx] ? titleRow.children[colIdx] : dt.column(colIdx).header();
  }

  function getFilterTh(dt, colIdx) {
    const headerRows = dt.table().header().querySelectorAll('tr');
    const filterRow = headerRows[1];
    return filterRow && filterRow.children[colIdx] ? filterRow.children[colIdx] : null;
  }

  function getFilterWidth(dt, colIdx) {
    const th = getFilterTh(dt, colIdx) || getTitleTh(dt, colIdx);
    const rect = th.getBoundingClientRect();
    return Math.max(140, Math.floor(rect.width));
  }

  // ---- Rendering into FILTER row -------------------------------------------
  function makeHistogramInFilterRow(dt, colIdx, options, d3) {
    const opts = Object.assign({}, DEFAULTS, options || {});
    const tblNode = dt.table().node();
    const tableId = tblNode.id || ('odc-' + Math.random().toString(36).slice(2));
    tblNode.id = tableId;

    injectStyles();

    const parser = utils.parseNumber;
    const values = dt.column(colIdx).data().toArray().map(parser).filter(v => v != null && isFinite(v));
    if (values.length === 0) return;

    const min = d3.min(values);
    const max = d3.max(values);

    const margin = opts.margin;
    const width = getFilterWidth(dt, colIdx) - margin.left - margin.right;
    const height = opts.height - margin.top - margin.bottom;

    const filterTh = $(getFilterTh(dt, colIdx));
    if (!filterTh.length) return;

    // Replace the existing input in the filter row
    filterTh.addClass('odc-numeric-filter').empty();

    const container = $('<div class="ods-histogram" aria-label="Histogram filter"></div>');
    const svgEl = $('<svg class="ods-histogram-svg" role="img"></svg>')
      .attr('width', width + margin.left + margin.right)
      .attr('height', height + margin.top + margin.bottom);
    container.append(svgEl);
    filterTh.append(container);

    const svg = d3.select(svgEl[0]).append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const x = d3.scaleLinear().domain([min, max]).range([0, width]);
    const bins = d3.histogram().domain(x.domain()).thresholds(x.ticks(opts.binCount))(values);
    const y = d3.scaleLinear().domain([0, d3.max(bins, d => d.length)]).nice().range([height, 0]);

    const bar = svg.selectAll('.bar')
      .data(bins)
      .enter().append('g')
      .attr('class', 'bar')
      .attr('transform', d => `translate(${x(d.x0)},${y(d.length)})`);

    bar.append('rect')
      .attr('x', 1)
      .attr('width', d => Math.max(0, x(d.x1) - x(d.x0) - 1))
      .attr('height', d => height - y(d.length))
      .attr('fill', opts.theme.barFill);

    const xAxis = d3.axisBottom(x).ticks(4).tickSize(3);
    svg.append('g').attr('class', 'axis axis--x').attr('transform', `translate(0,${height})`).call(xAxis);

    const brush = d3.brushX().extent([[0, 0], [width, height]]).on('brush end', brushed);
    svg.append('g').attr('class', 'brush').call(brush);

    // Update shared state and redraw table on brush
    const rangesForTable = tableRangeState.get(tableId) || [];
    tableRangeState.set(tableId, rangesForTable);

    function brushed(event) {
      const sel = event.selection;
      const key = colIdx;
      for (let i = rangesForTable.length - 1; i >= 0; i--) {
        if (rangesForTable[i].colIdx === key) rangesForTable.splice(i, 1);
      }
      if (!sel) { dt.draw(); return; }
      const [x0, x1] = sel;
      rangesForTable.push({ colIdx: key, min: x.invert(x0), max: x.invert(x1), parser });
      dt.draw();
    }

    container.attr('title', 'Drag to select a numeric range for filtering');
  }

  // ---- CKAN table discovery -------------------------------------------------
  function findCkanDatatablesTable() {
    const uuid = extractResourceIdFromUrl(window.location.pathname);
    if (uuid) {
      // Match resource URL or ajax URL containing the UUID
      let $t = $(`table[data-module="datatables_view"][data-resource-url*="${uuid}"]`);
      if ($t.length) return $t.first();
      $t = $(`table[data-module="datatables_view"][data-ajaxurl*="${uuid}"]`);
      if ($t.length) return $t.first();
    }
    const $fallback = $('table[data-module="datatables_view"]');
    return $fallback.length ? $fallback.first() : $('table.dataTable').first();
  }

  // ---- Public API -----------------------------------------------------------
  async function attach(selectorOrTableNode, options) {
    const $table = selectorOrTableNode ? $(selectorOrTableNode) : findCkanDatatablesTable();
    if (!$table || !$table.length) return;

    await waitForDataTables();
    registerGlobalRangeFilterOnce();

    const d3 = await waitForD3().catch(() => null);
    if (!d3) return; // D3 missing; skip histograms

    // Wait for DataTables to init the table (and build filter row)
    if (!$table.hasClass('dataTable') || !$table.data('DataTable')) {
      $table.on('init.dt', function () { renderForTable($table, options, d3); });
    } else {
      renderForTable($table, options, d3);
    }
  }

  function renderForTable($table, options, d3) {
    const dt = $table.DataTable ? $table.DataTable() : ($table.dataTable ? $table.dataTable().api() : null);
    if (!dt) return;

    const columns = dt.columns().indexes().toArray();

    columns.forEach(colIdx => {
      // Prefer CKAN's data-type hint on filter row if present
      const filterTh = getFilterTh(dt, colIdx);
      const dtype = filterTh ? filterTh.getAttribute('data-type') : null;
      const isNumeric = dtype && /^int|^float|^number|^numeric/i.test(dtype) ? true : utils.isNumericColumn(dt, colIdx);

      if (isNumeric) {
        makeHistogramInFilterRow(dt, colIdx, options, d3);
      }
    });

    // Recreate histograms if headers are rebuilt after redraws / visibility changes
    dt.on('draw', function () {
      columns.forEach(colIdx => {
        const filterTh = getFilterTh(dt, colIdx);
      if (!filterTh) return;
        if (!$(filterTh).find('.ods-histogram').length) {
          const dtype = filterTh.getAttribute('data-type');
          const isNumeric = dtype && /^int|^float|^number|^numeric/i.test(dtype) ? true : utils.isNumericColumn(dt, colIdx);
          if (isNumeric) makeHistogramInFilterRow(dt, colIdx, options, d3);
        }
      });
    });

    // Optional: send brush ranges to server in server-side mode. [3](https://designsystem.ontario.ca/)
    $table.on('preXhr.dt', function (e, settings, data) {
      const tableId = settings.nTable && settings.nTable.id ? settings.nTable.id : null;
      const ranges = tableRangeState.get(tableId) || [];
      data.odcRanges = ranges.map(r => ({ col: r.colIdx, min: r.min, max: r.max }));
    });
  }

  async function init(options) {
    const $t = findCkanDatatablesTable();
    if ($t && $t.length) await attach($t, options);
  }

  // Inject styles once
  injectStyles();

  return { init, attach, utils };
}));

// Auto-init on DOM ready
(function () {
  function boot() { window.OdcHistogram && window.OdcHistogram.init({ binCount: 24, height: 44 }); }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else { boot(); }
})();
