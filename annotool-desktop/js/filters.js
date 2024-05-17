
var isDragging = false;
$('#tbl_tpfltr_resizer')
.mousedown(function() {
    $(window).mousemove(function(e) {
        isDragging = true;		
		$('#tpfltr').height ( $(window).height() - e.clientY )
    });
    return false;
})
.mouseup(function() {
    var wasDragging = isDragging;
    isDragging = false;
    $(window).unbind("mousemove");
});

$('#resizer')
.mousedown(function() {
    $(window).mousemove(function(e) {
        isDragging = true;		
		$('#annos').height ( $(window).height() - e.clientY )
    });
    return false;
})
.mouseup(function() {
    var wasDragging = isDragging;
    isDragging = false;
    $(window).unbind("mousemove");
});

$('#colorseditresizer')
.mousedown(function() {
    $(window).mousemove(function(e) {
        isDragging = true;		
		$('#colorseditpanel').height ( $(window).height() - e.clientY )
    });
    return false;
})
.mouseup(function() {
    var wasDragging = isDragging;
    isDragging = false;
    $(window).unbind("mousemove");
});

function resetMe() {
	var myDiv = document.getElementById('annos');
	startWidth = parseInt(document.defaultView.getComputedStyle(myDiv).width, 10);
    startHeight = parseInt(document.defaultView.getComputedStyle(myDiv).height, 10);
	myDiv.style.width = startWidth + 'px';
	myDiv.style.height = startHeight + 'px';
}

$('#annosheader #toTop').click(function() {
    $('#annos').animate({ scrollTop:0 }, 100, 'swing' )
})

$('#annosheader #toBottom').click(function() {
    $('#annos').animate( { scrollTop: $('#allAnnos').height() }, 100, 'swing' )
})

function fltr_Next() {
    document.getElementById("fltr_next").blur();
	// var arr = Object.keys(allAnnotations.images);
	// var arr = $('#allAnnos').DataTable().column(1).data();
	var arr = $('#allAnnos tr').find('td:nth-child(2)').map(function(){ return $(this).text() }).get();
	arr.sort(alphanumCase)
	for ( i=0; i<arr.length; i++ ){
		if( parseInt(arr[i]) > parseInt(imName) ){
			if (brd && brd.renderer ) {
				if (imReadFlag) return !1;
				imReadFlag = !0;

				$("#allAnnos tr").removeClass("highlighted")
				$("#allAnnos td").filter( function() {	return $(this).text() == arr[i] } ).closest("tr").eq(0).addClass("highlighted");
				
				//	SCROLL TO
				var container = $('#annos'),
					elem = $('#allAnnos tr.highlighted');
				if ( 
					$(window).height() < $('#allAnnos tr.highlighted').offset().top + 20  	// exei kruftei apo kato	
					||	$('#allAnnos tr.highlighted').offset().top < $(window).height() - $('#annos').height() 	// exei kruftei apo pano	
				) {
					$('#annos').scrollTop( $('#annos').scrollTop() +$('#allAnnos tr.highlighted').position().top - 100 )
				}
				// $('a[data-dt-idx="5"]').click()	// show page of highlighted
				loadImg( allAnnotations.images[arr[i]].imageIndex )
			}
		break;
		}
	}
}

function fltr_Prev() {
    document.getElementById("fltr_prev").blur();
	// var arr = Object.keys(allAnnotations.images);
	// var arr = $('#allAnnos').DataTable().column(1).data();
	var arr = $('#allAnnos tr').find('td:nth-child(2)').map(function(){ return $(this).text() }).get();
	arr.sort(alphanumCase)
	arr.reverse();
	for ( i=0; i<arr.length; i++ ){
		if( parseInt(arr[i]) < parseInt(imName) ){
			if (brd && brd.renderer ) {
				if (imReadFlag) return !1;
				imReadFlag = !0;
				
				$("#allAnnos tr").removeClass("highlighted")
				$("#allAnnos td").filter( function() {	return $(this).text() == arr[i] } ).closest("tr").eq(0).addClass("highlighted");
				
				//	SCROLL TO
				var container = $('#annos'),
					elem = $('#allAnnos tr.highlighted');
				if ( 
					$(window).height() < $('#allAnnos tr.highlighted').offset().top + 20  	// exei kruftei apo kato	
					||	$('#allAnnos tr.highlighted').offset().top < $(window).height() - $('#annos').height() 	// exei kruftei apo pano	
				) {
					$('#annos').scrollTop( $('#annos').scrollTop() +$('#allAnnos tr.highlighted').position().top - 100 )
				}
				
				loadImg(allAnnotations.images[arr[i]].imageIndex)
			}
		break;
		}
	}
}

function showAnnos() {
	document.getElementById("showannos").blur();
    storeAnnotationImg();
    var a = JSON.stringify(allAnnotations);
    localStorage.allAnnotations = a;
	if ( $('table#allAnnos').html()!=="" ) { 
		$('table#allAnnos').DataTable().destroy(); 
	}
	$('#allAnnos').html("");
	var output ="<thead> <th class='select'></th> <th>Frame</th>  <th>Brand</th> <th>Touchpoint</th> <th>Duration</th> <th>Avg Hits</th>  <th>Total Hits</th> <th>Time</th>   <th>Location</th> <th>Size</th><th>solus</th>  </thead>";
	var annorows = commonExportData();
	annokeys=Object.keys(annorows);	// annokey = px: "34::Allstate::Bib"
	annokeys.sort(alphanumCase);
	var prev="", current="";
	for ( var i=0; i<annokeys.length; i++ ) {
		if ( prev.length>0 ) {	//an den einai to proto
			current = annokeys[i];
			if ( parseInt( current.split("::")[0] ) == parseInt( prev.split("::")[0] )+1 ) {	//CRITICAL
				for (j=0; j<annokeys.length-i; j++){
					if ( annokeys[i+j].split("::")[0] > annokeys[i].split("::")[0] ) {
						break;
					}
					if ( annorows.hasOwnProperty( prev.split("::")[0]+"::"+annokeys[i+j].split("::")[1]+"::"+annokeys[i+j].split("::")[2] ) ){
						prev = prev.split("::")[0]+"::"+annokeys[i+j].split("::")[1]+"::"+annokeys[i+j].split("::")[2]
						current = annokeys[i+j].split("::")[0]+"::"+annokeys[i+j].split("::")[1]+"::"+annokeys[i+j].split("::")[2]
						annorows[ current ].frameNum = annorows[ prev ].frameNum;
						annorows[ current ].hits += annorows[ prev ].hits;
						annorows[ current ].duration += annorows[ prev ].duration;
						var avgVal = annorows[ current ].hits/annorows[ current ].duration;
						if ( Math.round(avgVal) !== avgVal ) {
							annorows[ current ].avgHits = (annorows[ current ].hits/annorows[ current ].duration).toFixed(3);
						}
						annorows[ current ].location = annorows[ prev ].location;
						annorows[ current ].solus = annorows[ prev ].solus;
						delete annorows[ prev ];
					}
				}
			}
		}
		prev = annokeys[i];
	}
	var finalrows = annorows;
	var finalkeys = Object.keys(finalrows);
	finalkeys.sort(alphanumCase);
	for( d=0; d<finalkeys.length; d++ ){	// Brand, Touchpoint, Frame, Time, Duration, Total Hits, Avg Hits, Location, Size
		output +="<tr>"
		+"<td></td>"
		+"<td class='framescol'>"+( finalrows[ finalkeys[d] ].frameNum )+"</td>"
		+"<td id='brandscol' class='brandscol'>"+finalrows [ finalkeys[d] ].brand+"</td>"
		+"<td class='tpointscol'>"+finalrows [ finalkeys[d] ].tpoint+"</td>"
		+"<td>"+finalrows[ finalkeys[d] ].duration+"</td>"
		+"<td>"+finalrows[ finalkeys[d] ].avgHits+"</td>"
		+"<td>"+finalrows[ finalkeys[d] ].hits+"</td>"
		+"<td>"+finalrows[ finalkeys[d] ].time+"</td>"
		+"<td>"+finalrows[ finalkeys[d] ].location+"</td>"
		+"<td>"+finalrows[ finalkeys[d] ].size.toFixed(3)+"</td>"
		+"<td>"+finalrows[ finalkeys[d] ].solus+"</td>"
		+"</tr>"
		;
	}
	document.getElementById('allAnnos').innerHTML = output;
	if ( $('#imageName').val().length==5 ) {
		var a = document.getElementsByClassName('framescol');  // force 5 digits to framescol // not working
		for(i=0; i<a.length; i++){
			var b = a[i].innerHTML.replace(/(<([^>]+)>)/ig,"");
			var pad = "00000"
			var c = pad.substring(0, pad.length - b.length) + b;
			b=c;
			a[i].innerHTML=b
		}
	}
	annoDataTable()
	$('#annocontent').width( $('#allAnnos').width() + 10 )
	framesClick()
}

function framesClick(){
	$("td.framescol").click( function() {
		if ( $(this).text()!==imName ) {
			loadImg ( imIndices.indexOf( $(this).text() ) )
			$("#allAnnos tr").removeClass("highlighted")
			$(this).parent().addClass("highlighted")
		}
	});
}

/////	FILTERED NAVIGATION (TO DO)
	next_imName = imIndices[imIndex+1];
	next_imIndex = imIndex+1;

function filter_loadImg(a) {
    if (0 < nullAnnoFlag) return alert("You have some NULL annotations. Fix any NULL issues before proceeding."), imReadFlag = !1;
    (a !== imIndex || 2 < brd.objectsList) && filter_prepareChangeImg();
    prev_imIndex = imIndex;
    prev_imName = imIndices[imIndex];
    imName = imIndices[a];
    imIndex = a;
	
    if (0 != imIndices.length) {
        a = new FileReader;
        a.onloadend = function(a) {
            var b = new Image;
            b.onload = function() {
                b.width == imWidth && b.height == imHeight && void 0 !== im ? im.url = a.target.result : (imWidth = b.width, imHeight = b.height, 730 < imWidth && (imAspectRatio =
                    imWidth / imHeight, imWidth = Math.abs(730), imHeight = 1 / imAspectRatio * imWidth), void 0 !== im && brd.removeObject(im), im = brd.create("image", [a.target.result, [1, imHeight],
                    [imWidth, imHeight]
                ], {
                    layer: 0,
                    highlightFillColor: "none",
                    hightlighted: "off"
                }), im.visProp.highlight = !1, im.isDraggable = !1, document.getElementById("box").setAttribute("style", "width:" + imWidth + "px;height:" + imHeight + "px;"), brd.resizeContainer(imWidth, imHeight), brd.setBoundingBox([1, 1, imWidth, imHeight], !1));
                brd.update();
                filter_afterChangeImg();
                imReadFlag = !1
            };
            b.src = a.target.result
        };
        try {
            return a.readAsDataURL(imAll[imName]), document.getElementById("imageName").value = imName, !1
        } catch (b) {
            return imIndex = prev_imIndex, imName = imIndices[imIndex], document.getElementById("imageName").value = imName, alert("Could not load requested image."), !0
        }
    }
}

function filter_prepareChangeImg() {
    brd.off("up");
    brd.off("move");
    brd.off("update");
    storeAnnotationImg();
    storeEXIFdataImg();
    highlightAllObj();
    0 != highlighted.length && storePreset(0);
    removeAllObj()
}

function filter_afterChangeImg() {
    allAnnotations.currentImage = imName;
	resetGUIAnnoInfo();
	filter_loadAnnotationImg()
}

function filter_loadAnnotationImg() {	//// gia to filtro
	if (allAnnotations.images.hasOwnProperty(imName)) {
		var a = allAnnotations.images[imName].annotations;
		for (i=0 ; i < a.length; i++){
			if (a[i].brand.toString().indexOf("Investec") == 0){
				brd.suspendUpdate();
				for (var b = 0, c = a.length; b < c; b++) createPolygon(a[b].startPoint, a[b].diagPoint).annotation = {
					brand: a[b].brand,
					tpoint: a[b].tpoint,
					hits: a[b].hits
				};
				brd.unsuspendUpdate();
			}
		}
    }
}




