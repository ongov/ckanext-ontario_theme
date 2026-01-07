
(function ($, d3) {
  'use strict';

  $(function () {
    const $serverTable = $('table[data-module="datatables_view"]').first();
    if ($serverTable.length === 0) return;

    function log(...args) {
      console.log('[odc-datatables-histograms]', ...args);
    }

    function getCssVar(name, fallback) {
      const val = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
      return val || fallback;
    }

    const ODS_COLORS = {
      secondaryActive: getCssVar('--ontario-colour-secondary-active', '#C2E0FF'),
      focus: getCssVar('--ontario-colour-focus', '#009ADB')
    };

    function isNumericType(t) {
      t = String(t || '').toLowerCase();
      return ['int', 'float', 'numeric', 'double', 'money', 'number', 'real', 'decimal'].some((p) => t.startsWith(p));
    }

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

    function createClientRegion(fields, odsOptions) {
      const $wrapper = $serverTable.closest('.dataTables_wrapper');

      const tableClassList = [
        'ontario-table',
        'ontario-table--full-container-width'
      ];
      if (odsOptions.condensed) tableClassList.push('ontario-table--condensed');
      if (odsOptions.noZebraStripes) tableClassList.push('ontario-table--no-zebra-stripes');

      const captionHtml = odsOptions.caption ? `<caption>${odsOptions.caption}</caption>` : '';

      const $region = $(`
        <div id="odc-client-region" class="ontario-table-container">
          <div class="ontario-table-div">
            <table id="odc-client-dt" class="${tableClassList.join(' ')} dataTable no-footer" style="width:100%">
              ${captionHtml}
              <thead>
                <tr class="odc-head-row"></tr>
                <tr class="odc-filter-row"></tr>
              </thead>
              <tbody></tbody>
            </table>
          </div>
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
        const isNumeric = isNumericType(f.type) && f.id !== '_id';
        const th = $(`<th scope="col"${isNumeric ? ' class="ontario-table-cell--numeric"' : ''}>${f.id}</th>`);
        $headRow.append(th);

        const filterCell = $(`<th class="odc-filter-cell" data-col-id="${f.id}"></th>`);
        $filterRow.append(filterCell);
      });

      return $region;
    }

    function initClientSideDataTable($region, allData, fields, odsOptions) {
      const $clientTable = $region.find('#odc-client-dt');
      const columns = fields.map((f) => ({ title: f.id, data: f.id }));
      const idIndex = fields.findIndex((f) => f.id === '_id');

      const numericIndices = fields
        .map((f, i) => (isNumericType(f.type) && f.id !== '_id' ? i : -1))
        .filter((i) => i >= 0);

      const defaultRowHeaderIndex =
        typeof odsOptions.rowHeaderIndex === 'number'
          ? odsOptions.rowHeaderIndex
          : (fields.length && !isNumericType(fields[0].type) ? 0 : null);

      const columnDefs = [];
      if (idIndex >= 0) columnDefs.push({ targets: [idIndex], visible: false });
      if (numericIndices.length > 0) {
        columnDefs.push({
          targets: numericIndices,
          className: 'ontario-table-cell--numeric'
        });
      }

      return $clientTable.DataTable({
        data: allData,
        columns: columns,
        columnDefs: columnDefs,
        orderCellsTop: true,
        fixedHeader: false,
        paging: true,
        searching: true,
        ordering: true,
        deferRender: true,
        autoWidth: false,
        serverSide: false,
        processing: false,
        dom: 'lfrtip',

        headerCallback: function (thead) {
          const $ths = $(thead).find('tr.odc-head-row th');
          $ths.attr('scope', 'col');
          $ths.each(function (i) {
            const f = fields[i];
            if (f && isNumericType(f.type) && f.id !== '_id') {
              $(this).addClass('ontario-table-cell--numeric');
            }
          });
        },

        createdRow: function (row) {
          if (defaultRowHeaderIndex == null) return;
          const $cells = $('td', row);
          if ($cells.length === 0) return;
          const $rowHeaderCell = $cells.eq(defaultRowHeaderIndex);
          const th = document.createElement('th');
          th.setAttribute('scope', 'row');
          th.innerHTML = $rowHeaderCell.html();
          const cls = ($rowHeaderCell.attr('class') || '').split(/\s+/).filter(Boolean);
          cls.forEach((c) => th.classList.add(c));
          th.classList.remove('ontario-table-cell--numeric');
          $rowHeaderCell.replaceWith(th);
        }
      });
    }

    const filters = { state: { text: {}, ranges: {} } };

    function hasAnyActiveFilter(filters) {
      const hasText = Object.values(filters.state.text).some((v) => v && v.trim().length > 0);
      const hasRanges = Object.keys(filters.state.ranges).length > 0;
      return hasText || hasRanges;
    }

    function filterRecords(records, fields) {
      const fieldIndexById = {};
      fields.forEach((f, i) => (fieldIndexById[f.id] = i));

      return records.filter((row) => {
        for (const [colId, term] of Object.entries(filters.state.text)) {
          if (!term) continue;
          const cell = (row[colId] ?? '').toString().toLowerCase();
          if (!cell.includes(term.toLowerCase())) return false;
        }
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
        for (const [colId, term] of Object.entries(filters.state.text)) {
          if (!term) continue;
          const idx = fieldIndexById[colId];
          if (idx == null) continue;
          const cell = (data[idx] || '').toString().toLowerCase();
          if (!cell.includes(term.toLowerCase())) return false;
        }
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

    let histograms = [];

    function renderHeaderControls($region, dt, fields, allData) {
      histograms = [];
      const $cells = $region.find('.odc-filter-cell');

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
            if (val) filters.state.text[colId] = val;
            else delete filters.state.text[colId];
            dt.draw();
            const subset = hasAnyActiveFilter(filters) ? filterRecords(allData, fields) : [];
            updateAllHistogramOverlays(subset);
          });
          cell.appendChild(input);
          return;
        }

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

        g.append('g')
          .attr('transform', `translate(0,${innerH})`)
          .call(d3.axisBottom(x).ticks(4).tickSize(3))
          .call((gx) => gx.selectAll('text').attr('font-size', 9))
          .call((gx) => gx.selectAll('path,line').attr('stroke', '#d9d9d9'));

        const brush = d3.brushX()
          .extent([[0, 0], [innerW, innerH]])
          .on('end', function brushed(event) {
            if (!event.selection) {
              delete filters.state.ranges[colId];
            } else {
              const [x0, x1] = event.selection.map(x.invert);
              filters.state.ranges[colId] = [x0, x1];
            }
            dt.draw();
            const subset = hasAnyActiveFilter(filters) ? filterRecords(allData, fields) : [];
            updateAllHistogramOverlays(subset);
          });

        g.append('g').attr('class', 'brush').call(brush);

        svg.on('dblclick', () => {
          delete filters.state.ranges[colId];
          dt.draw();
          g.select('.brush').call(brush.move, null);
          const subset = hasAnyActiveFilter(filters) ? filterRecords(allData, fields) : [];
          updateAllHistogramOverlays(subset);
        });

        histograms.push({ colId, bin, x, y, innerH, overlaySel });
      });

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
        const subset = hasAnyActiveFilter(filters) ? filterRecords(allData, fields) : [];
        updateAllHistogramOverlays(subset);
      }

      $(window).on('resize', debounce(rerenderAllHists, 200));
      dt.on('columns.adjust', debounce(rerenderAllHists, 200));
    }

    function updateAllHistogramOverlays(filteredRecords) {
      if (!histograms || histograms.length === 0) return;
      const hasSubset = filteredRecords && filteredRecords.length > 0;

      histograms.forEach((h) => {
        const overlayValues = hasSubset
          ? filteredRecords.map((r) => +r[h.colId]).filter((v) => Number.isFinite(v))
          : [];
        const overlayBins = h.bin(overlayValues);

        if (!hasSubset || !hasAnyActiveFilter(filters)) {
          h.overlaySel.attr('y', h.innerH).attr('height', 0);
        } else {
          h.overlaySel
            .data(overlayBins)
            .attr('y', (d) => h.y(d.length))
            .attr('height', (d) => h.innerH - h.y(d.length));
        }
      });
    }

    const resourceId = getResourceId();
    if (!resourceId) {
      log('Could not determine resource_id. Aborting.');
      return;
    }

    (async function run() {
      try {
        const { allRecords, fields } = await fetchAllData(resourceId);
        log(`Fetched ${allRecords.length} records from resource ${resourceId}.`);

        const odsOptions = {
          caption: $serverTable.data('caption') || null,
          condensed: true,
          noZebraStripes: false,
          rowHeaderIndex: null
        };

        const $region = createClientRegion(fields, odsOptions);
        const dt = initClientSideDataTable($region, allRecords, fields, odsOptions);
        attachGlobalFilter(dt, fields);
        renderHeaderControls($region, dt, fields, allRecords);

        dt.draw();
        updateAllHistogramOverlays([]);
      } catch (err) {
        console.error('[odc-datatables-histograms] Error:', err);
      }
    })();
  });
})(jQuery, d3);
