// From: https://docs.ckan.org/en/2.9/theming/javascript.html
// Calls the ckan.module() function to register a new JavaScript module with CKAN.
// -------------------------------------------------------------------------------

// Enable JavaScript's strict mode. Strict mode catches some common
// programming errors and throws exceptions, prevents some unsafe actions from
// being taken, and disables some confusing and bad JavaScript features.
// "use strict";

console.log('in module')


function myFunction(resourceUrl, orgName, pkgTitle, groupName) {

  console.log('CLICKED !!!! file: ', resourceUrl)
  let fileName = resourceUrl.split('download/')[1];
  console.log('this_file: ', fileName)
  console.log('org_name: ', orgName)
  console.log('pkg.title: ', pkgTitle)
  console.log('groupName: ', groupName)

  if (groupName.length > 2) { 
    // clean = groupName.replaceAll('&#39;','"').replaceAll('u"','"');
    // groupName = JSON.parse("[" + clean + "]")[0][0]['name'];
    groupName = "TBD";
  } else {
    groupName = "";
  }   

  window.dataLayer = window.dataLayer || [];
  window.dataLayer.push({
    'event': 'File Download',
    'ministryTag': orgName,
    'group': groupName,
    'datasetName': pkgTitle,
    'dataResourceName': fileName
  });
  

  // Object.keys(myarray).forEach(key => console.log(myarray[key]));

}