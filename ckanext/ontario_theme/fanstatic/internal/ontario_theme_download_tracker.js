// Enable JavaScript's strict mode. Strict mode catches some common
// programming errors and throws exceptions, prevents some unsafe actions from
// being taken, and disables some confusing and bad JavaScript features.
"use strict";

function trackDownload(resourceUrl, orgName, pkgTitle, groupName) {

  let fileName = resourceUrl.split('download/')[1];

  console.log('groupName: ', groupName)

  window.dataLayer = window.dataLayer || [];
  window.dataLayer.push({
    'event': 'File Download',
    'ministryTag': orgName,
    'group': groupName,
    'datasetName': pkgTitle,
    'dataResourceName': fileName
  });
}
