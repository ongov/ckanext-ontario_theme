// src/main.jsx
import React from 'react';
import { createRoot } from 'react-dom/client';
import { FlatUiTable } from '@portaljs/components';

console.log('[PortalJS] bundle loaded');

function App({ csvUrl }) {
  if (!csvUrl) {
    console.warn('[PortalJS] No csvUrl provided to App');
    return null;
  }
  return <FlatUiTable csvUrl={csvUrl} pageSize={25} searchable sortable />;
}

// Global guard to prevent double mounting in CKAN dev mode
if (!window.__portaljs_mounted__) {
  window.__portaljs_mounted__ = true;

  document.addEventListener('DOMContentLoaded', () => {
    const mount = document.getElementById('portaljs-table-root');
    if (!mount) {
      console.warn('[PortalJS] #portaljs-table-root not found; skipping mount');
      return;
    }

    if (mount.hasAttribute('data-react-mounted')) {
      console.warn('[PortalJS] Already mounted, skipping');
      return;
    }
    mount.setAttribute('data-react-mounted', 'true');

    // Clear any existing content to avoid React error #299
    mount.innerHTML = '';

    const csvUrl = mount.dataset.csvUrl;
    console.log('[PortalJS] mount:', mount);
    console.log('[PortalJS] csvUrl:', csvUrl);

    try {
      console.log('[PortalJS] mount.innerHTML:', mount.innerHTML);
      createRoot(mount).render(<App csvUrl={csvUrl} />);
      console.log('[PortalJS] React app mounted successfully');
    } catch (err) {
      console.error('[PortalJS] Error mounting React app:', err);
    }
  });
} else {
  console.warn('[PortalJS] Global guard: already initialized, skipping');
}
