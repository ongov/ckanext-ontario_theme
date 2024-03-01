//Shows the feedback module once a related dataset link is clicked on from the previous page

var feedbackForm = document.getElementById('related-dataset-feedback-form');
var relatedDatasetLinks = document.querySelectorAll('#related-datasets-right-module a');

relatedDatasetLinks.forEach(function(link) {
  link.addEventListener('click', function(event) {
    feedbackForm.style.display = 'block'; 
  });
});