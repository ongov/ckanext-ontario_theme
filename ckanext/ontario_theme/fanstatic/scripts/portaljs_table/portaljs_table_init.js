console.log('Initializing FlatUiTable...');
const { FlatUiTable } = PortalJSComponents;
const mountNode = document.getElementById('portaljs-table-root');
const csvUrl = mountNode.getAttribute('data-csv-url');

ReactDOM.render(
  React.createElement(FlatUiTable, { url: csvUrl }),
  mountNode
);
