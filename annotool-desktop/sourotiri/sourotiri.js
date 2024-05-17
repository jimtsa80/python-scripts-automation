$(document).ready(function(){
	$('img').click(function(){
		if ($(this).hasClass('selected')) {
			$(this).removeClass('selected') 
		}
		else {
			$(this).addClass('selected');
		}
	});
 });
 
var soura = document.getElementById("souraFolder")

soura.addEventListener("change", function(a) {
    a = document.getElementById("projectFolderBox");
    if (0 === soura.files.length) return !1;
	
    var b = soura.files[0].webkitRelativePath.replace(/\\/g, "/"),
        b = b.substring(0, b.lastIndexOf("/") + 1);
    "" !== prefs.imgFoldername ? prefs.imgFoldername !== b ? (msg1 = "CAUTION: The folder you have selected is different than the one you ", msg2 = " Are you sure you want to proceed ?", confirm(msg1 + msg2) && (initJSXBoard(), prefs.imgFoldername = b, a.value = 0 < allAnnotations.imageNum ? "[" + allAnnotations.imageNum +
        " files]  " + b : "")) : (initJSXBoard(), a.value = 0 < allAnnotations.imageNum ? "[" + allAnnotations.imageNum + " files]  " + b : "") : (initJSXBoard(), 0 < allAnnotations.imageNum && (prefs.imgFoldername = b, a.value = "[" + allAnnotations.imageNum + " files]  " + b));
    soura.blur();
		var optDiv = document.getElementById('workspace');
		var b,c = "";

		b = "css/video.css"; c=optDiv.getElementsByTagName('option')[0].value;	
	});
	
function generateImgs(){
	imList = document.getElementById("souraFolder").files;

	console.log(imList)
	
}