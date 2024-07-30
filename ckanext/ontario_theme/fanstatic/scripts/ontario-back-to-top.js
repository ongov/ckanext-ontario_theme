window.addEventListener('scroll', function () {
	let scroll = document.getElementById('actual-btt-button');
	let nav = document.getElementById('about-page-navigation'); 
	if (nav) {
        let onThisPageNav = document.querySelector('#about-page-navigation .ontario-page-navigation-content--full');
        let skipToMainDiv = document.getElementById('skip-to-main');
        let threshold = onThisPageNav.offsetHeight + skipToMainDiv.offsetTop - onThisPageNav.offsetTop;
        scroll.classList.toggle('active', window.scrollY > threshold);
	}
	else {
	scroll.classList.toggle('active', window.scrollY > 200);
	}
});

function scrollToTop() {
	window.scrollTo({ top: 0, left: 0, behavior: 'smooth' });
}