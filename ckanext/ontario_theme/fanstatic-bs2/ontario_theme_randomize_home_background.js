// Enable JavaScript's strict mode. Strict mode catches some common
// programming errors and throws exceptions, prevents some unsafe actions from
// being taken, and disables some confusing and bad JavaScript features.
"use strict";

ckan.module('ontario_theme_randomize_home_background', function ($) {
  return {
    initialize: function () {
      var background_images = [
        '1097_converted.jpg',
        '3909_converted.jpg',
        '3911_converted.jpg',
        '3921_converted.jpg',
        '9969_converted.jpg',
        'alexandre-godreau-510220-unsplash_converted.jpg',
        'artem-bali-570693-unsplash_converted.jpg',
        'carlos-muza-84523-unsplash_converted.jpg',
        'j-334395-unsplash_converted.jpg',
        'markus-spiske-109588-unsplash_converted.jpg',
        'PL10574_0R8A8746_converted.jpg',
        'PL10576_0R8A8752_converted.jpg',
        'PL10593_0R8A8791_converted.jpg',
        'PL10906_0R8A2865_converted.jpg',
        'richard-balog-647377-unsplash_converted.jpg'
      ]

      var random_int = Math.floor((Math.random() * background_images.length));
      this.el[0].style.backgroundImage = "linear-gradient(0deg,rgba(0,0,0,0.6),rgba(0,0,0,0.6)), url(/images/backgrounds/" + 
                                          background_images[random_int] + ")";
    }
  };
});