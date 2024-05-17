function changebg() {
	var color = document.getElementById('page').style.backgroundColor = "#"+document.getElementById('mybg').value; // cached
	// $('input#mybg').css('background-color',color+"!important");
}

function boxBorders() {
	boxborder = "#"+document.getElementById('boxborder').value; // cached
	$('.col1 canvas').css( 'border-color', boxborder );
}

function boxBorderWidth() {
	boxborderwidth = document.getElementById('boxborderwidth').value;
	$('.col1 canvas').css( 'border-width', boxborderwidth );
}

function highlightStrokeColor() {
	highlightstrokecolor = "#"+document.getElementById('highlightstrokecolor').value; // cached
	$('.col2 canvas').css( 'border-color', highlightstrokecolor );
}

function highlightStrokeColorWidth() {
	highlightstrokecolorwidth = document.getElementById('highlightstrokecolorwidth').value;
	$('.col2 canvas').css( 'border-width', highlightstrokecolorwidth );
}

function mouseoverFillColor() {
	mouseoverfillcolor = "#"+document.getElementById('mouseoverfillcolor').value; // cached
}

function dotStrokeColor() {
	dotstrokecolor = "#"+document.getElementById('dotstrokecolor').value; // cached
}