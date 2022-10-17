// Enable JavaScript's strict mode. Strict mode catches some common
// programming errors and throws exceptions, prevents some unsafe actions from
// being taken, and disables some confusing and bad JavaScript features.
"use strict";

function trackDownload(resourceUrl, orgName, pkgTitle, groupName) {

  let fileName;
  let urlArray;
  urlArray = resourceUrl.split('/');
  fileName = urlArray[urlArray.length - 1];

  window.dataLayer = window.dataLayer || [];
  window.dataLayer.push({
    'event': 'File Download',
    'ministryTag': orgName,
    'group': groupName,
    'datasetName': pkgTitle,
    'dataResourceName': fileName
  });

  console.log('dataLayer: ', dataLayer)
}
