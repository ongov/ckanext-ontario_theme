
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

  // Helper: extract resource UUID from /resource/<uuid> in a URL
  function extractResourceIdFromUrl(url) {
    if (!url) return null;
    var m = String(url).match(/\/resource\/([0-9a-f-]{36})/i);
    return m ? m[1] : null;
  }

  // Helper: is numeric from second header row type hint (eg data-type="int4")
  function thTypeIsNumeric(tableEl, colIdx) {
    try {
      var typeRowThs = tableEl.querySelectorAll('thead tr:nth-child(2) th');
      var th = typeRowThs && typeRowThs[colIdx];
      if (!th) return null;
      var t = (th.getAttribute('data-type') || '').toLowerCase();
      if (!t) return null;
      // Proper alternation regex (fixes previous newline-based pattern)
      return /(int|numeric|float|real|double|decimal|smallint|bigint)/.test(t);
    } catch (e) {
      return null;
    }
  }

  // --- inject filters row into thead AFTER DataTables init ---
  function addFiltersRow(tableEl) {
    var thead = tableEl.querySelector('thead');
    if (!thead) { log('no thead'); return; }
    // If the theme already provides a second <tr> with header inputs, skip injection
    var existingFilterInputs = thead.querySelectorAll('tr input[type="search"], tr .fhead input');
    if (existingFilterInputs.length > 0) {
      log('filters row already provided by theme; skip injection');
      return;
    }
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
      svg.setAttribute('height', '36'); // visible in tight headers
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

  // Ensure a tooling cell to host SVG + input for column idx
  function ensureToolingCell(tableEl, colIdx) {
    var $thead = $(tableEl).find('thead');
    // Preferred: our injected filters row
    var $toolCell = $thead.find('tr.odc-dt-filters-row th').eq(colIdx);
    if ($toolCell.length) return $toolCell;
    // Fallback: theme-provided second header row
    $toolCell = $thead.find('tr:nth-child(2) th').eq(colIdx);
    if ($toolCell.length) return $toolCell;
    // Last resort: inject our filters row then return
    addFiltersRow(tableEl);
    return $thead.find('tr.odc-dt-filters-row th').eq(colIdx);
  }

  // Create/find an SVG inside the tooling cell and wrap existing input nicely
  function ensureHistogramSvg($toolCell) {
    // Find any existing svg
    var svg = $toolCell.find('svg.odc-dt-col-hist')[0];
    // Wrap existing input with our container and add SVG above it
    var $existingInput = $toolCell.find('input[type="search"], input.odc-dt-col-search').first();
    var hasContainer = $toolCell.find('.odc-dt-header-tool').length > 0;

    if (!hasContainer) {
      var $wrap = $('<div class="odc-dt-header-tool"></div>');
      if (svg) $wrap.append(svg);
      if ($existingInput.length) {
        $existingInput.appendTo($wrap);
      } else {
        $wrap.append('<input type="search" class="ontario-input odc-dt-col-search" placeholder="Filter…" aria-label="Filter column">');
      }
      $toolCell.empty().append($wrap);
    }
    // Ensure an SVG exists at the top of the wrapper
    svg = $toolCell.find('svg.odc-dt-col-hist')[0];
    if (!svg) {
      svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('width', '100%');
      svg.setAttribute('height', '36');
      svg.classList.add('odc-dt-col-hist');
      $toolCell.find('.odc-dt-header-tool').prepend(svg);
    }
    return svg;
  }

  function guessIsNumeric(dt, colIdx) {
    var dataSample = dt.column(colIdx).data().slice(0, 50);
    var len = dataSample.length;
    var numericCount = 0;
    for (var i = 0; i < len; i++) {
      var v = dataSample[i];
      if (v !== null && v !== undefined && String(v).trim() !== '') {
        var n = Number(v);
        if (!isNaN(n)) numericCount++;
      }
    }
    if (len <= 5) return numericCount >= 1;
    return (numericCount / len) >= 0.6;
  }

  // Fallback: build bins from current column data client-side
  function buildHistogramFromColumn(dt, colIdx, numBins) {
    var raw = dt.column(colIdx).data().toArray();
    var values = raw.map(function (x) { return Number(x); }).filter(function (v) { return !isNaN(v); });
    if (!values.length) return { bins: [], min: NaN, max: NaN };

    var min = Math.min.apply(null, values);
    var max = Math.max.apply(null, values);
    var span = max - min;
    var bins = [];
    var step = span / numBins;
    if (!isFinite(step) || step <= 0) step = 1;

    for (var i = 0; i < numBins; i++) {
      bins.push({ x0: min + i * step, x1: min + (i + 1) * step, count: 0 });
    }
    values.forEach(function (v) {
      var idx = Math.floor((v - min) / step);
      if (idx < 0) idx = 0;
      if (idx >= numBins) idx = numBins - 1;
      bins[idx].count++;
    });
    return { bins: bins, min: min, max: max };
  }

  // ---- CSRF-aware POST helper ----
  function getCkanCsrfToken() {
    try {
      var nameMeta = document.querySelector('meta[name="csrf_field_name"]');
      var tokenMeta = document.querySelector('meta[name="_csrf_token"]');
      var fieldName = nameMeta && nameMeta.content;
      var token = tokenMeta && tokenMeta.content;
      return { fieldName: fieldName, token: token };
    } catch (e) {
      return { fieldName: null, token: null };
    }
  }

  // Robust Action API POST with JSON body, CSRF header and optional API key
  async function postAction(url, payload, opts) {
    const csrf = getCkanCsrfToken();
    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    };
    if (csrf && csrf.token) headers['X-CSRF-Token'] = csrf.token;
    if (opts && opts.apiKey) headers['X-CKAN-API-Key'] = opts.apiKey;

    const resp = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
      credentials: 'same-origin'
    });
    const ctype = (resp.headers.get('content-type') || '').toLowerCase();
    const body = ctype.includes('application/json') ? await resp.json() : (await resp.text());
    if (!ctype.includes('application/json')) {
      const snippet = typeof body === 'string' ? body.slice(0, 200) : String(body).slice(0, 200);
      console.warn('[ODC hist] non-JSON from', url, 'status', resp.status, 'type', ctype, 'snippet:', snippet);
    }
    return { ok: resp.ok, status: resp.status, body };
  }

  // Build histogram bins via CKAN datastore_search_sql (server-side)
  async function buildHistogram(resourceId, field, numBins, opts) {
    try {
      // 1) min/max via SQL (POST)
      const sqlMinMax = `SELECT MIN("${field}") AS min, MAX("${field}") AS max FROM "${resourceId}"`;
      const { body: mmJson } = await postAction('/api/3/action/datastore_search_sql', { sql: sqlMinMax }, opts);

      if (!mmJson || !mmJson.success || !mmJson.result || !mmJson.result.records || !mmJson.result.records.length) {
        log('min/max query failed or non-JSON/empty', mmJson);
        return { bins: [], min: NaN, max: NaN };
      }
      const min = Number(mmJson.result.records[0].min);
      const max = Number(mmJson.result.records[0].max);
      log('min/max', min, max);
      if (!isFinite(min) || !isFinite(max) || min === max) {
        return { bins: [], min, max };
      }

      // 2) bins via width_bucket (POST)
      const sqlBins = `
        SELECT width_bucket("${field}", ${min}, ${max}, ${numBins}) AS b, COUNT(*) AS c
        FROM "${resourceId}"
        WHERE "${field}" IS NOT NULL
        GROUP BY b
        ORDER BY b
      `;
      const { body: json } = await postAction('/api/3/action/datastore_search_sql', { sql: sqlBins }, opts);

      if (!json || !json.success || !json.result || !Array.isArray(json.result.records)) {
        log('bins query failed or non-JSON payload', json);
        return { bins: [], min, max };
      }

      const step = (max - min) / numBins;
      const bins = json.result.records.map(function (r) {
        var idx = Math.max(0, Math.min(numBins - 1, Number(r.b) - 1)); // clamp 0..n-1
        return { x0: min + idx * step, x1: min + (idx + 1) * step, count: Number(r.c) };
      });
      log('bins via SQL', bins.length);
      return { bins, min, max };
    } catch (err) {
      log('SQL histogram error', err);
      return { bins: [], min: NaN, max: NaN };
    }
  }

  function renderHeaderHistogram(svg, bins, min, max, onBrush) {
    // If header momentarily reports 0 size, fall back to sane defaults
    var rect = svg.getBoundingClientRect();
    const w = (svg.clientWidth || rect.width || 120);
    const h = (svg.clientHeight || rect.height || 36);
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
  async function resolveFieldName(resourceId, headerText, colIdx, opts) {
    try {
      const { body: info } = await postAction('/api/3/action/datastore_info', { id: resourceId }, opts);
      if (!info || !info.success || !info.result || !info.result.fields) {
        log('datastore_info failed; fallback to header text', info);
        return headerText.trim();
      }
      const fields = info.result.fields;
      const byLabel = fields.find(f =>
        (((f.info && f.info.label) || f.label || '').trim() === headerText.trim())
      );
      if (byLabel) return byLabel.id;
      return fields[colIdx] ? fields[colIdx].id : headerText.trim();
    } catch (err) {
      log('datastore_info error', err);
      return headerText.trim();
    }
  }

  function initForTable(tableEl, opts) {
    var dt = $(tableEl).DataTable();
    // Install persistent range filter holder on this table
    if (!tableEl._odcRangeFilters) tableEl._odcRangeFilters = {};

    // Get resourceId from table dataset or parse from data-resource-url
    var ds = tableEl.dataset || {};
    var resourceId = ds.moduleResourceId || ds.resourceId || null;
    if (!resourceId) {
      resourceId = extractResourceIdFromUrl(ds.resourceUrl || tableEl.getAttribute('data-resource-url'));
    }
    if (!resourceId) {
      var modEl = $(tableEl).closest('[data-module="datatables_view"], [data-module="datatables-view"]').get(0);
      if (modEl && modEl.dataset) {
        var md = modEl.dataset;
        resourceId = md.moduleResourceId || md.resourceId || extractResourceIdFromUrl(md.resourceUrl);
      }
    }
    log('resourceId resolved:', resourceId);

    // Install global hook once (shared across tables)
    if (!$.fn.dataTable.ext.search._odcInstalled) {
      $.fn.dataTable.ext.search.push(function (settings, data /*, dataIndex */) {
        var nTable = settings.nTable;
        var ranges = nTable && nTable._odcRangeFilters || {};
        for (var colIdxStr in ranges) {
          if (!Object.prototype.hasOwnProperty.call(ranges, colIdxStr)) continue;
          var range = ranges[colIdxStr];
          var v = Number(data[Number(colIdxStr)]);
          if (isNaN(v) || v < range[0] || v > range[1]) return false;
        }
        return true;
      });
      $.fn.dataTable.ext.search._odcInstalled = true;
    }

    dt.columns().every(function (colIdx) {
      var headerCell = $(dt.column(colIdx).header());
      var $toolCell = ensureToolingCell(tableEl, colIdx);
      if (!$toolCell || !$toolCell.length) return;

      var $input = $toolCell.find('input[type="search"], input.odc-dt-col-search').first();

      // Determine numeric-ness: prefer type hint; fallback to data sampling
      var isNum = thTypeIsNumeric(tableEl, colIdx);
      if (isNum === null) isNum = guessIsNumeric(dt, colIdx);
      log('col', colIdx, 'isNum', isNum);

      var headerText = headerCell.text().trim();
      log('col', colIdx, 'headerText', headerText);

      // Skip CKAN system column _id for histogram; show input instead
      if (headerText === '_id') {
        if ($input.length) {
          // Ensure text filter works for _id if desired
          $input.off('keyup.change.odc').on('keyup change', function () {
            dt.column(colIdx).search(this.value).draw();
          });
        }
        return;
      }

      if (isNum && resourceId) {
        var svg = ensureHistogramSvg($toolCell);
        if ($input.length) { $input.hide(); }

        resolveFieldName(resourceId, headerText, colIdx, opts).then(function (fieldName) {
          log('col', colIdx, 'fieldName', fieldName);

          // First try server-side SQL binning
          buildHistogram(resourceId, fieldName, 24, opts).then(function (res) {
            var bins = res.bins, min = res.min, max = res.max;

            // If SQL fails or returns empty, fallback to client-side binning
            if (!bins.length || !isFinite(min) || !isFinite(max)) {
              log('SQL bins empty; using client-side bins for col', colIdx);
              var client = buildHistogramFromColumn(dt, colIdx, 24);
              bins = client.bins; min = client.min; max = client.max;
            }

            if (!bins.length) {
              log('no bins to render; show text input again for col', colIdx);
              if ($input.length) { $input.show(); }
              return;
            }

            // Clear any previous chart content before rendering anew
            d3.select(svg).selectAll('*').remove();
            renderHeaderHistogram(svg, bins, min, max, function (range) {
              if (!range) {
                delete tableEl._odcRangeFilters[colIdx];
              } else {
                tableEl._odcRangeFilters[colIdx] = range;
              }
              dt.draw();
            });
          }).catch(function (err) {
            log('histogram build error; fallback to input', err);
            if ($input.length) { $input.show(); }
          });
        }).catch(function (err) {
          log('resolveFieldName error; fallback to input', err);
          if ($input.length) { $input.show(); }
        });

      } else {
        // Non-numeric: wire text search
        if ($input.length) {
          $input.off('keyup.change.odc').on('keyup change', function () {
            dt.column(colIdx).search(this.value).draw();
          });
        }
      }
    });
  }

  // Hook once the DataTable is initialized
  $(document).on('init.dt', function (e, settings) {
    var tableEl = settings.nTable; // DOM table for this DataTable
    // Run only on tables that explicitly declare datatables_view
    if (!tableEl.hasAttribute('data-module') || tableEl.getAttribute('data-module') !== 'datatables_view') {
      return;
    }
    // Try to inject our filters row (will skip if theme already provides inputs)
    addFiltersRow(tableEl);

    // Optional: supply an API key via data attribute on the table (e.g., data-api-key="..."),
    // or inject via a global variable window.CKAN_API_KEY set in the page template.
    var apiKey = (tableEl.getAttribute('data-api-key') || window.CKAN_API_KEY || '').trim();
    var opts = apiKey ? { apiKey: apiKey } : undefined;

    // Initialize histograms & filters
    initForTable(tableEl, opts);
  });

})(jQuery, window, document);
