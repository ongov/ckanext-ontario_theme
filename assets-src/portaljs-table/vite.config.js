import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  resolve: {
    dedupe: ['react', 'react-dom'] // ✅ Prevent multiple React copies
  },
  esbuild: {
    jsx: 'automatic', // ✅ Ensures react/jsx-runtime is bundled
    jsxImportSource: 'react'
  },
  build: {
    minify: false, // ✅ Keep readable for CKAN dev
    outDir: '/usr/lib/ckan/default/src/ckanext-ontario_theme/ckanext/ontario_theme/fanstatic/scripts', // ✅ Absolute path to CKAN fanstatic
    emptyOutDir: false, // ✅ Avoid wiping other CKAN assets
    target: 'es2017',
    rollupOptions: {
      input: './src/main.jsx', // ✅ Your React entry point
      external: [], // ✅ Force bundling everything (React, ReactDOM, PortalJS)
      output: {
        format: 'iife', // ✅ CKAN doesn’t support ES modules easily
        inlineDynamicImports: true,
        entryFileNames: 'portaljs_table.bundle.js', // ✅ Matches webassets.yml
        assetFileNames: (info) =>
          info.name && info.name.endsWith('.css')
            ? 'portaljs_table.bundle.css'
            : 'portaljs_table.[ext]'
      }
    }
  }
});
