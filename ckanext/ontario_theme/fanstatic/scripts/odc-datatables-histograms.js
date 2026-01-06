/*
Builds a client-side DataTable using the same jQuery DataTables library and styles, 
and embeds the brushable histograms in the second header row.

global jQuery, d3 
*/

(function ($, d3) {
  'use strict';

  $(function () {
    const $serverTable = $('table[data-module="datatables_view"]').first();
    if ($serverTable.length === 0) return;

    function log(...args) {
      console.log('[odc-datatables-histograms]', ...args);
    }

    // --- ODS color resolver: read CSS variables and fallback to hex --------
    function getCssVar(name, fallback) {
      const val = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
      return val || fallback;
    }
    const ODS_COLORS = {
      secondaryActive: getCssVar('--ontario-colour-secondary-active', '#C2E0FF'), // underlay (always-on full histogram)
      focus: getCssVar('--ontario-colour-focus', '#009ADB')                        // overlay (filtered subset)
    };

    function getResourceId() {
      const attr = $serverTable.attr('data-resource-id') || $serverTable.data('resource-id');
      if (attr) return attr;
      if (window.ckan && window.ckan.resource && window.ckan.resource.id) return window.ckan.resource.id;
      const match = window.location.pathname.match(/\/resource\/([0-9a-fA-F-]{36})/);
      if (match && match[1]) return match[1];
      return null;
    }

    async function fetchAllData(resourceId) {
      const url = '/api/3/action/datastore_search';
      const limit = 500;
      let offset = 0;
      const allRecords = [];
      let fields = null;

      while (true) {
        const qs = `?resource_id=${encodeURIComponent(resourceId)}&limit=${limit}&offset=${offset}`;
        const res = await fetch(url + qs);
        const json = await res.json();
        const { records, fields: resultFields } = json.result;
        if (!fields && Array.isArray(resultFields)) {
          fields = resultFields.map((f) => ({ id: f.id, type: f.type }));
        }
        allRecords.push(...records);
        if (records.length < limit) break;
        offset += limit;
      }

      if (!fields && allRecords.length > 0) {
        fields = Object.keys(allRecords[0]).map((k) => ({ id: k, type: 'text' }));
      }

      return { allRecords, fields };
    }

    function createClientRegion(fields) {
      const $wrapper = $serverTable.closest('.dataTables_wrapper');
      const $region = $(`
        <div id="odc-client-table-region" style="margin-top: 12px;">
          <table id="odc-client-dt" class="table table-striped table-hover" style="width:100%">
            <thead>
              <tr class="odc-head-row"></tr>
              <tr class="odc-filter-row"></tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      `);

      if ($wrapper.length) {
        $wrapper.hide();
        $wrapper.after($region);
      } else {
        $serverTable.hide();
        $serverTable.after($region);
      }

      const $headRow = $region.find('.odc-head-row');
      const $filterRow = $region.find('.odc-filter-row');

      fields.forEach((f) => {
        $headRow.append(`<th>${f.id}</th>`);
        $filterRow.append(`<th class="odc-filter-cell" data-col-id="${f.id}"></th>`);
      });

      return $region;
    }

    function initClientSideDataTable($region, allData, fields) {
      const $clientTable = $region.find('#odc-client-dt');
      const columns = fields.map((f) => ({ title: f.id, data: f.id }));
      const idIndex = fields.findIndex((f) => f.id === '_id');
      const columnDefs = [];
      if (idIndex >= 0) columnDefs.push({ targets: [idIndex], visible: false });

      return $clientTable.DataTable({
        data: allData,
        columns: columns,
        columnDefs: columnDefs,
        orderCellsTop: true,
        fixedHeader: true,
        paging: true,
        searching: true,
        ordering: true,
        deferRender: true,
        autoWidth: false,
        serverSide: false,
        processing: false,
        dom: 'lfrtip'
      });
    }

    // ---- Filter state, helpers, and DT global search ----------------------
    const filters = { state: { text: {}, ranges: {} } };

    function hasAnyActiveFilter(filters) {
      const hasText = Object.values(filters.state.text).some((v) => v && v.trim().length > 0);
      const hasRanges = Object.keys(filters.state.ranges).length > 0;
      return hasText || hasRanges;
    }

    function filterRecords(records, fields) {
      // Use same logic as DataTables ext.search for consistency.
      const fieldIndexById = {};
      fields.forEach((f, i) => (fieldIndexById[f.id] = i));

      return records.filter((row) => {
        // Text filters (contains, case-insensitive)
        for (const [colId, term] of Object.entries(filters.state.text)) {
          if (!term) continue;
          const cell = (row[colId] ?? '').toString().toLowerCase();
          if (!cell.includes(term.toLowerCase())) return false;
        }

        // Numeric range filters (intersection)
        for (const [colId, rng] of Object.entries(filters.state.ranges)) {
          if (!rng || rng.length !== 2) continue;
          const v = parseFloat(row[colId]);
          if (!Number.isFinite(v)) return false;
          if (v < rng[0] || v > rng[1]) return false;
        }

        return true;
      });
    }

    function attachGlobalFilter(dt, fields) {
      const fieldIndexById = {};
      fields.forEach((f, i) => (fieldIndexById[f.id] = i));

      $.fn.dataTable.ext.search.push(function (settings, data) {
        if (dt.settings()[0] !== settings) return true;

        // Text filters
        for (const [colId, term] of Object.entries(filters.state.text)) {
          if (!term) continue;
          const idx = fieldIndexById[colId];
          if (idx == null) continue;
          const cell = (data[idx] || '').toString().toLowerCase();
          if (!cell.includes(term.toLowerCase())) return false;
        }

        // Numeric ranges
        for (const [colId, rng] of Object.entries(filters.state.ranges)) {
          if (!rng || rng.length !== 2) continue;
          const idx = fieldIndexById[colId];
          if (idx == null) continue;
          const v = parseFloat(data[idx]);
          if (!Number.isFinite(v)) return false;
          if (v < rng[0] || v > rng[1]) return false;
        }

        return true;
      });
    }

    // ---- Header histograms (underlay + overlay) ---------------------------
    // Keep references so we can update overlay bars for ALL histograms.
    let histograms = []; // array of { colId, bin, x, y, innerH, overlaySel }

    function renderHeaderControls($region, dt, fields, allData) {
      histograms = []; // reset and rebuild

      const $cells = $region.find('.odc-filter-cell');
      const isNumericType = (t) => {
        t = String(t || '').toLowerCase();
        return ['int', 'float', 'numeric', 'double', 'money', 'number', 'real', 'decimal'].some((p) => t.startsWith(p));
      };

      $cells.each(function () {
        const cell = this;
        const colId = cell.getAttribute('data-col-id');
        const field = fields.find((f) => f.id === colId);
        const isNumeric = field && isNumericType(field.type) && colId !== '_id';

        if (!isNumeric) {
          const input = document.createElement('input');
          input.type = 'text';
          input.className = 'form-control input-sm';
          input.placeholder = 'Search';
          input.style.width = '100%';
          input.addEventListener('input', function () {
            const val = this.value || '';
            if (val) filters.state.text[colId] = val; else delete filters.state.text[colId];
            dt.draw();
            // Update overlays across ALL histograms after text filter change
            const subset = hasAnyActiveFilter(filters) ? filterRecords(allData, fields) : [];
            updateAllHistogramOverlays(subset);
          });
          cell.appendChild(input);
          return;
        }

        // Numeric histogram with underlay + overlay
        const values = allData.map((d) => +d[colId]).filter((v) => Number.isFinite(v));
        const w = cell.getBoundingClientRect().width || 180;
        const h = 42;
        const margin = { top: 2, right: 4, bottom: 14, left: 4 };

        const svg = d3.select(cell).append('svg')
          .attr('width', w)
          .attr('height', h)
          .attr('class', 'odc-histogram');

        const innerW = w - margin.left - margin.right;
        const innerH = h - margin.top - margin.bottom;
        const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

        const x = d3.scaleLinear().domain(d3.extent(values)).nice().range([0, innerW]);
        const bin = d3.bin().domain(x.domain()).thresholds(x.ticks(16));
        const bins = bin(values);
        const y = d3.scaleLinear().domain([0, d3.max(bins, (d) => d.length)]).nice().range([innerH, 0]);

        // Underlay bars (full histogram)
        g.selectAll('.underlay')
          .data(bins)
          .enter()
          .append('rect')
          .attr('class', 'underlay ontario-colour-secondary-active')
          .attr('x', (d) => x(d.x0) + 1)
          .attr('y', (d) => y(d.length))
          .attr('width', (d) => Math.max(0, x(d.x1) - x(d.x0) - 2))
          .attr('height', (d) => innerH - y(d.length))
          .attr('fill', ODS_COLORS.secondaryActive);

        // Overlay bars (will reflect the filtered subset, across ALL filters)
        const overlaySel = g.selectAll('.overlay')
          .data(bins)
          .enter()
          .append('rect')
          .attr('class', 'overlay ontario-colour-focus')
          .attr('x', (d) => x(d.x0) + 1)
          .attr('width', (d) => Math.max(0, x(d.x1) - x(d.x0) - 2))
          .attr('y', innerH)
          .attr('height', 0)
          .attr('fill', ODS_COLORS.focus);

        // Optional tiny axis
        g.append('g')
          .attr('transform', `translate(0,${innerH})`)
          .call(d3.axisBottom(x).ticks(4).tickSize(3))
          .call((gx) => gx.selectAll('text').attr('font-size', 9))
          .call((gx) => gx.selectAll('path,line').attr('stroke', '#d9d9d9'));

        // Brush on THIS column: changes filters.state.ranges[colId] and updates table + overlays
        const brush = d3.brushX()
          .extent([[0, 0], [innerW, innerH]])
          .on('end', function brushed(event) {
            if (!event.selection) {
              delete filters.state.ranges[colId];
            } else {
              const [x0, x1] = event.selection.map(x.invert);
              filters.state.ranges[colId] = [x0, x1];
            }

            // Redraw table (DataTables ext.search uses filters.state)
            dt.draw();

            // Update overlay bars for ALL histograms using the globally filtered subset
            const subset = hasAnyActiveFilter(filters) ? filterRecords(allData, fields) : [];
            updateAllHistogramOverlays(subset);
          });

        g.append('g').attr('class', 'brush').call(brush);

        // Double-click to clear this column's brush
        svg.on('dblclick', () => {
          delete filters.state.ranges[colId];
          dt.draw();
          g.select('.brush').call(brush.move, null);
          const subset = hasAnyActiveFilter(filters) ? filterRecords(allData, fields) : [];
          updateAllHistogramOverlays(subset);
        });

        // Store refs for global overlay updates
        histograms.push({
          colId,
          bin,      // bin generator with same domain/thresholds
          x,
          y,
          innerH,
          overlaySel
        });
      });

      // Re-render on window resize / column adjust to keep widths aligned
      const debounce = (fn, wait) => {
        let t = null;
        return function () {
          clearTimeout(t);
          t = setTimeout(() => fn.apply(this, arguments), wait);
        };
      };
      function rerenderAllHists() {
        $region.find('.odc-filter-cell').empty();
        renderHeaderControls($region, dt, fields, allData);
        // After re-render, update overlays to reflect current filter state
        const subset = hasAnyActiveFilter(filters) ? filterRecords(allData, fields) : [];
        updateAllHistogramOverlays(subset);
      }
      $(window).on('resize', debounce(rerenderAllHists, 200));
      dt.on('columns.adjust', debounce(rerenderAllHists, 200));
    }

    // Update overlays for ALL histograms to reflect the current filtered subset.
    function updateAllHistogramOverlays(filteredRecords) {
      if (!histograms || histograms.length === 0) return;

      const hasSubset = filteredRecords && filteredRecords.length > 0;

      histograms.forEach((h) => {
        // Compute overlay values for THIS histogram's column from the filtered subset
        const overlayValues = hasSubset
          ? filteredRecords.map((r) => +r[h.colId]).filter((v) => Number.isFinite(v))
          : [];

        // Use same bin generator (same domain/thresholds) so arrays align
        const overlayBins = h.bin(overlayValues);

        // If no active filters, clear overlays; else render overlay counts
        if (!hasSubset || !hasAnyActiveFilter(filters)) {
          h.overlaySel
            .attr('y', h.innerH)
            .attr('height', 0);
        } else {
          h.overlaySel
            .data(overlayBins)
            .attr('y', (d) => h.y(d.length))
            .attr('height', (d) => h.innerH - h.y(d.length));
        }
      });
    }

    // ---- Main --------------------------------------------------------------
    const resourceId = getResourceId();
    if (!resourceId) {
      log('Could not determine resource_id. Aborting.');
      return;
    }

    (async function run() {
      try {
        const { allRecords, fields } = await fetchAllData(resourceId);
        log(`Fetched ${allRecords.length} records from resource ${resourceId}.`);

        const $region = createClientRegion(fields);
        const dt = initClientSideDataTable($region, allRecords, fields);

        attachGlobalFilter(dt, fields);

        renderHeaderControls($region, dt, fields, allRecords);

        // Initial draw and overlay state (no filters → overlays cleared)
        dt.draw();
        updateAllHistogramOverlays([]); // ensure overlays start empty
      } catch (err) {
        console.error('[odc-datatables-histograms] Error:', err);
      }
    })();
  });
})(jQuery, d3);
