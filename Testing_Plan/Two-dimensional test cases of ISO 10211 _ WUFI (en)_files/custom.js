jQuery(document).ready(function() {
	jQuery(window).bind('scroll', function(e) {
		hefct();
	});		
});
  	
    	
function hefct() {
	var scrollPosition = jQuery(window).scrollTop();
	jQuery('#parallax-bg').css('top', (0 - (scrollPosition * .2)) + 'px');
}	