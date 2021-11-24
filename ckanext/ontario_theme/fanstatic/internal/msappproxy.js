$(document).ready(function () {
	var proxy_url = "catalogue-ontariogov.msappproxy.net"
	var non_proxy_url = "intra.catalogue.ogo.tbs.gov.on.ca"
	if (document.domain == proxy_url) {
		$('[href*="'+non_proxy_url+'"]').attr("href", function() {
			var hyperlink_reference = $(this).attr("href")
			$(this).attr("href", hyperlink_reference.replace(non_proxy_url, proxy_url))
		})	
		$('a:contains('+non_proxy_url+')').text(function() {
			var hr_text = $(this).text()
			$(this).text(hr_text.replace(non_proxy_url, proxy_url))
		})	
	}
})
