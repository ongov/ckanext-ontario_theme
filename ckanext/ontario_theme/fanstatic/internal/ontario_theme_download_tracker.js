// Enable JavaScript's strict mode. Strict mode catches some common
// programming errors and throws exceptions, prevents some unsafe actions from
// being taken, and disables some confusing and bad JavaScript features.
"use strict";

function trackDownload(resourceUrl, orgName, pkgTitle, groupName) {

  let fileName = resourceUrl.split('download/')[1];

  if (groupName.length > 2) { 
    // clean = groupName.replaceAll('&#39;','"').replaceAll('u"','"');
    // groupName = JSON.parse("[" + clean + "]")[0][0]['name'];
    groupName = "TBD";
  } else {
    groupName = "";
  }
  console.log('groupName after fix: ', groupName)

  window.dataLayer = window.dataLayer || [];
  window.dataLayer.push({
    'event': 'File Download',
    'ministryTag': orgName,
    'group': groupName,
    'datasetName': pkgTitle,
    'dataResourceName': fileName
  });
}
