
/* odc-datatables-histograms.js
 * Adds per-column header filters and numeric histograms with D3 brush
 * Depends on: jQuery, DataTables, D3 v7
 */
(function ($, window, document) {
  'use strict';

  // --- tiny logger for quick debugging ---
  function log() {
    var args = Array.prototype.slice.call(arguments);
    args.unshift('[ODC hist]');
    if (window.console && console.log) console.log.apply(console, args);
  }

  // --- inject filters row into thead AFTER DataTables init ---
  function addFiltersRow(tableEl) {
    var thead = tableEl.querySelector('thead');
    if (!thead) { log('no thead'); return; }
    if (thead.querySelector('tr.odc-dt-filters-row')) { log('filters row already present'); return; }

    var firstRow = thead.querySelector('tr');
    if (!firstRow) { log('no first header row'); return; }

    var filtersRow = firstRow.cloneNode(true);
    filtersRow.classList.add('odc-dt-filters-row');

    filtersRow.querySelectorAll('th').forEach(function (th) {
      th.innerHTML = '';
      th.classList.add('odc-dt-filter-cell');

      var wrap = document.createElement('div');
      wrap.className = 'odc-dt-header-tool';

      var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('width', '100%');
      svg.setAttribute('height', '36');                // visible in tight headers
      svg.classList.add('odc-dt-col-hist');

      var input = document.createElement('input');
      input.type = 'search';
      input.className = 'ontario-input odc-dt-col-search';
      input.placeholder = 'Filter…';
      input.setAttribute('aria-label', 'Filter column');

      wrap.appendChild(svg);
      wrap.appendChild(input);
      th.appendChild(wrap);
    });

    thead.appendChild(filtersRow);
    log('filters row injected');
  }
    
  function guessIsNumeric(dt, colIdx) {
    var dataSample = dt.column(colIdx).data().slice(0, 50);
    var len = dataSample.length;
    var numericCount = 0;

    for (var i = 0; i < len; i++) {
      var v = dataSample[i];
      // Accept numeric strings, integers, floats; ignore blanks
      if (v !== null && v !== undefined && String(v).trim() !== '') {
        var n = Number(v);
        if (!isNaN(n)) numericCount++;
      }
    }

    if (len <= 5) {
      // For tiny samples, at least one numeric value is enough
      return numericCount >= 1;
    }
    // For larger samples, require >=60% numeric
    return (numericCount / len) >= 0.6;
  }

  async function buildHistogram(resourceId, field, numBins) {
    // 1) min/max
    const sqlMinMax = `SELECT MIN("${field}") AS min, MAX("${field}") AS max FROM "${resourceId}"`;
    const mmResp = await fetch('/api/3/action/datastore_search_sql', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sql: sqlMinMax })
    });
    const mmJson = await mmResp.json();
    if (!mmJson.success || !mmJson.result || !mmJson.result.records || !mmJson.result.records.length) {
      return { bins: [], min: NaN, max: NaN };
    }
    const min = Number(mmJson.result.records[0].min);
    const max = Number(mmJson.result.records[0].max);
    if (!isFinite(min) || !isFinite(max) || min === max) {
      return { bins: [], min, max };
    }

    // 2) bins
    const sqlBins = `
      SELECT width_bucket("${field}", ${min}, ${max}, ${numBins}) AS b, COUNT(*) AS c
      FROM "${resourceId}"
      WHERE "${field}" IS NOT NULL
      GROUP BY b
      ORDER BY b
    `;
    const resp = await fetch('/api/3/action/datastore_search_sql', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sql: sqlBins })
    });
    const json = await resp.json();
    if (!json.success || !json.result || !json.result.records) {
      return { bins: [], min, max };
    }

    const step = (max - min) / numBins;
    const bins = json.result.records.map(function (r) {
      var idx = Math.max(0, Math.min(numBins - 1, Number(r.b) - 1));
      return { x0: min + idx * step, x1: min + (idx + 1) * step, count: Number(r.c) };
    });
    return { bins, min, max };
  }

  function renderHeaderHistogram(svg, bins, min, max, onBrush) {
    const w = svg.clientWidth || svg.getBoundingClientRect().width || 120;
    const h = svg.clientHeight || svg.getBoundingClientRect().height || 36;
    const m = { top: 2, right: 2, bottom: 2, left: 2 };
    const iw = Math.max(1, w - m.left - m.right);
    const ih = Math.max(1, h - m.top - m.bottom);

    const d3svg = d3.select(svg)
      .attr('viewBox', `0 0 ${w} ${h}`)
      .attr('preserveAspectRatio', 'none');

    const g = d3svg.append('g').attr('transform', `translate(${m.left},${m.top})`);
    const x = d3.scaleLinear().domain([min, max]).range([0, iw]);
    const y = d3.scaleLinear().domain([0, d3.max(bins, d => d.count) || 1]).range([ih, 0]);

    g.selectAll('rect.odc-hbar')
      .data(bins)
      .enter()
      .append('rect')
      .attr('class', 'odc-hbar')
      .attr('x', d => x(d.x0))
      .attr('y', d => y(d.count))
      .attr('width', d => Math.max(1, x(d.x1) - x(d.x0)))
      .attr('height', d => ih - y(d.count))
      .attr('fill', '#4f5d7a');

    const brush = d3.brushX()
      .extent([[0, 0], [iw, ih]])
      .on('end', function (event) {
        const sel = event.selection;
        if (!sel) { onBrush(null); return; }
        onBrush([x.invert(sel[0]), x.invert(sel[1])]);
      });

    g.append('g').attr('class', 'odc-hbrush').call(brush);
  }

  // Resolve datastore field id from header text (in case label != id)
  async function resolveFieldName(resourceId, headerText, colIdx) {
    const resp = await fetch('/api/3/action/datastore_info', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: resourceId })
    });
    const info = await resp.json();
    if (!info.success || !info.result || !info.result.fields) return headerText.trim();

    const fields = info.result.fields;
    // try label match first
    const byLabel = fields.find(f => (f.label || '').trim() === headerText.trim());
    if (byLabel) return byLabel.id;
    // fallback by index if header order == field order
    return fields[colIdx] ? fields[colIdx].id : headerText.trim();
  }

  function initForTable(tableEl) {
    var dt = $(tableEl).DataTable();

    // Try to read resource id from table or nearby module element
    var resourceId = tableEl.dataset && tableEl.dataset.resourceId;
    if (!resourceId) {
      var modEl = document.querySelector('[data-module="datatables_view"], [data-module="datatables-view"]');
      resourceId = modEl && modEl.dataset && (modEl.dataset.resourceId || modEl.dataset.moduleResourceId);
    }

    var filtersRow = tableEl.querySelector('thead tr.odc-dt-filters-row');
    if (!filtersRow) { log('no filters row present after init'); return; }

    dt.columns().every(function (colIdx) {
      var headerCell = $(dt.column(colIdx).header());
      var toolCell = headerCell.closest('thead').find('tr.odc-dt-filters-row th').eq(colIdx);
      if (!toolCell.length) return;

      var input = toolCell.find('input.odc-dt-col-search');
      var svg = toolCell.find('svg.odc-dt-col-hist')[0];
      if (!svg) return;

      var isNum = guessIsNumeric(dt, colIdx);

      if (isNum && resourceId) {
        input.hide();

        var headerText = headerCell.text().trim();
        resolveFieldName(resourceId, headerText, colIdx).then(function (fieldName) {
          buildHistogram(resourceId, fieldName, 24).then(function ({ bins, min, max }) {
            if (!bins.length) { input.show(); return; }
            renderHeaderHistogram(svg, bins, min, max, function (range) {
              if (!range) { dt.column(colIdx).search('').draw(); return; }
              $.fn.dataTable.ext.search.push(function (settings, data) {
                var v = Number(data[colIdx]);
                if (isNaN(v)) return false;
                return v >= range[0] && v <= range[1];
              });
              dt.draw();
              $.fn.dataTable.ext.search.pop();
            });
          }).catch(function () { input.show(); });
        });
      } else {
        input.on('keyup change', function () {
          dt.column(colIdx).search(this.value).draw();
        });
      }
    });
  }

  // Hook once the DataTable is initialized
  $(document).on('init.dt', function (e, settings) {
    var tableEl = settings.nTable; // DOM table for this DataTable
    // Support both module attribute styles
    if (!tableEl.matches('table[data-module="datatables_view"], table[data-module="datatables-view"]')) return;
    addFiltersRow(tableEl);
    initForTable(tableEl);
  });

})(jQuery, window, document);
