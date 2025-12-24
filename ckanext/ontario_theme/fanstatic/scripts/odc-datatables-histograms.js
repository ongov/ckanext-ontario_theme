
/* odc-datatables-histograms.js
 * Adds per-column header filters and numeric histograms with D3 brush
 * Depends on: jQuery, DataTables, D3 v7
*/
(function ($, window, document) {
  'use strict';

  function guessIsNumeric(dt, colIdx) {
    var col = dt.column(colIdx);
    var dataSample = col.data().slice(0, 50);
    var numericCount = 0;
    for (var i = 0; i < dataSample.length; i++) {
      var n = Number(dataSample[i]);
      if (!isNaN(n)) numericCount++;
    }
    return numericCount >= Math.max(5, dataSample.length * 0.6);
  }

  async function buildHistogram(resourceId, field, numBins) {
    const sqlMinMax = `
      SELECT MIN("${field}") AS min, MAX("${field}") AS max
      FROM "${resourceId}"
    `;
    const mmResp = await fetch('/api/3/action/datastore_search_sql', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sql: sqlMinMax })
    });
    const mmJson = await mmResp.json();
    const min = Number(mmJson.result.records[0].min);
    const max = Number(mmJson.result.records[0].max);
    if (!isFinite(min) || !isFinite(max) || min === max) {
      return { bins: [], min, max };
    }

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

    const step = (max - min) / numBins;
    const bins = json.result.records.map((r) => {
      var idx = Math.max(0, Math.min(numBins - 1, Number(r.b) - 1));
      return { x0: min + idx * step, x1: min + (idx + 1) * step, count: Number(r.c) };
    });
    return { bins, min, max };
  }

  function renderHeaderHistogram(svg, bins, min, max, onBrush) {
    const w = svg.clientWidth || svg.getBoundingClientRect().width;
    const h = svg.clientHeight || svg.getBoundingClientRect().height;
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

  function init() {
    // Use table[data-module="datatables_view"] instead of #resource-data
    var tableEl = document.querySelector('table[data-module="datatables_view"]');
    if (!tableEl) return;

    var dt = $(tableEl).DataTable();

    // Read resource id directly from the table’s dataset
    var resourceId = tableEl.dataset.resourceId || null;

    // Build tools for each column
    dt.columns().every(function (colIdx) {
      var headerCell = $(dt.column(colIdx).header());
      var toolCell = headerCell.closest('thead').find('tr.odc-dt-filters-row th').eq(colIdx);
      if (!toolCell.length) return;

      var input = toolCell.find('input.odc-dt-col-search');
      var svg = toolCell.find('svg.odc-dt-col-hist')[0];

      var isNum = guessIsNumeric(dt, colIdx);

      if (isNum && resourceId) {
        input.hide();
        // Derive field name: CKAN DataTables uses column config; fallback to header text
        var fieldName = dt.settings()[0].aoColumns[colIdx].data || headerCell.text().trim();

        buildHistogram(resourceId, fieldName, 24).then(function ({ bins, min, max }) {
          if (!bins.length) { input.show(); return; }
          renderHeaderHistogram(svg, bins, min, max, function (range) {
            if (!range) { dt.column(colIdx).search('').draw(); return; }
            // Apply a numeric range filter via DataTables global search hook for this draw
            $.fn.dataTable.ext.search.push(function (settings, data) {
              var v = Number(data[colIdx]);
              if (isNaN(v)) return false;
              return v >= range[0] && v <= range[1];
            });
            dt.draw();
            $.fn.dataTable.ext.search.pop();
          });
        }).catch(function () { input.show(); });

      } else {
        input.on('keyup change', function () {
          dt.column(colIdx).search(this.value).draw();
        });
      }
    });
  }

  $(document).ready(function () {
    // Only run if our filters row exists (injected by the snippet)
    if (document.querySelector('table[data-module="datatables_view"] thead tr.odc-dt-filters-row')) {
      init();
    }
  });

})(jQuery, window, document);
