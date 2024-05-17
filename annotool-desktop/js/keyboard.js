Mousetrap.bind(['ctrl'], function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1; ctrlPressed = !0 });
Mousetrap.bind(['ctrl'], function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1; ctrlPressed = !1 }, "keyup");

Mousetrap.bind(['a'], function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1; loadPrevImg() });
Mousetrap.bind(['s'], function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1; loadNextImg() });

Mousetrap.bind(['shift+a'], function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1; loadPrev10Img() });
Mousetrap.bind(['shift+s'], function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1; loadNext10Img() });

// Mousetrap.bind(['ctrl+s'], function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1; loadNextImg();	pastePreset(9) });
// Mousetrap.bind(['shift+d'], function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1; loadNextImg(); pastePreset('end') });

/* Mousetrap.bind(['shift+a'], function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1; goBackImg() }); */
Mousetrap.bind(['z'], function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1; removeHighlightedObj() });
Mousetrap.bind(['x'], function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1; removeAllObj() });
Mousetrap.bind(['c'], function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1; storeD('end') });
Mousetrap.bind(['v'], function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1; highlightAllObj() });
Mousetrap.bind(['f'], function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1; dehighlightAllObj() });
Mousetrap.bind({
    'shift+1': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('1') },
    'shift+2': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('2') },
    'shift+3': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('3') },
    'shift+4': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('4') },
    'shift+5': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('5') },
    'shift+6': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('6') },
    'shift+7': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('7') },
    'shift+8': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('8') },
    'shift+9': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('9') },
	'shift+0': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('0') },
	
	'shift+alt+1': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+1') },
    'shift+alt+2': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+2') },
    'shift+alt+3': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+3') },
    'shift+alt+4': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+4') },
    'shift+alt+5': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+5') },
    'shift+alt+6': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+6') },
    'shift+alt+7': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+7') },
    'shift+alt+8': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+8') },
    'shift+alt+9': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+9') },
	'shift+alt+0': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+0') },
	//
	'shift+q': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('q') },
	'shift+w': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('w') },
	'shift+e': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('e') },
	'shift+r': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('r') },
	'shift+t': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('t') },
	'shift+y': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('y') },
	'shift+u': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('u') },
	'shift+i': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('i') },
	'shift+o': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('o') },
	'shift+p': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('p') },
	
	'shift+alt+q': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+q') },
	'shift+alt+w': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+w') },
	'shift+alt+e': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+e') },
	'shift+alt+r': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+r') },
	'shift+alt+t': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+t') },
	'shift+alt+y': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+y') },
	'shift+alt+u': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+u') },
	'shift+alt+i': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+i') },
	'shift+alt+o': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+o') },
	'shift+alt+p': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+p') },
	//
	'shift+g': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('g') },
	'shift+h': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('h') },
	'shift+j': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('j') },
	'shift+k': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('k') },
	'shift+l': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('l') },
	'shift+b': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('b') },
	'shift+n': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('n') },
	'shift+m': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('m') },
	
	'shift+alt+g': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+g') },
	'shift+alt+h': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+h') },
	'shift+alt+j': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+j') },
	'shift+alt+k': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+k') },
	'shift+alt+l': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+l') },
	'shift+alt+b': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+b') },
	'shift+alt+n': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+n') },
	'shift+alt+m': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+m') },
	//
	'shift+f1': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('f1')  },
	'shift+f2': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('f2')  },
	'shift+f3': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('f3')  },
	'shift+f4': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('f4')  },
	'shift+f5': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('f5')  },
	'shift+f6': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('f6')  },
	'shift+f7': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('f7')  },
	'shift+f8': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('f8')  },
	'shift+f9': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('f9')  },
	'shift+f10': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1; storePreset('f10') },
	'shift+f11': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1; storePreset('f11') },
	'shift+f12': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1; storePreset('f12') },
	'ctrl+c': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+f12') },
	
	'shift+alt+f1': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+f1')  },
	'shift+alt+f2': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+f2')  },
	'shift+alt+f3': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+f3')  },
	'shift+alt+f4': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+f4')  },
	'shift+alt+f5': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+f5')  },
	'shift+alt+f6': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+f6')  },
	'shift+alt+f7': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+f7')  },
	'shift+alt+f8': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+f8')  },
	'shift+alt+f9': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  storePreset('alt+f9')  },
	'shift+alt+f10': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1; storePreset('alt+f10') },
	'shift+alt+f11': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1; storePreset('alt+f11') },
	'shift+alt+f12': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1; storePreset('alt+f12') },
});
Mousetrap.bind({
    '1': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('1') },
    '2': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('2') },
    '3': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('3') },
    '4': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('4') },
    '5': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('5') },
    '6': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('6') },
    '7': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('7') },
    '8': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('8') },
    '9': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('9') },
	'0': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('0') },
	
    'alt+1': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+1') },
    'alt+2': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+2') },
    'alt+3': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+3') },
    'alt+4': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+4') },
    'alt+5': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+5') },
    'alt+6': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+6') },
    'alt+7': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+7') },
    'alt+8': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+8') },
    'alt+9': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+9') },
	'alt+0': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+0') },
	//
	'q': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('q') } ,
	'w': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('w') } ,
	'e': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('e') } ,
	'r': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('r') } ,
	't': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('t') } ,
	'y': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('y') } ,
    'u': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('u') },
	'i': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('i') },
	'o': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('o') },
	'p': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('p') },
	
	'alt+q': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+q') } ,
	'alt+w': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+w') } ,
	'alt+e': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+e') } ,
	'alt+r': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+r') } ,
	'alt+t': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+t') } ,
	'alt+y': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+y') } ,
    'alt+u': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+u') },
	'alt+i': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+i') },
	'alt+o': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+o') },
	'alt+p': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+p') },
	//
	'g': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('g') },
	'h': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('h') },
	'j': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('j') },
	'k': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('k') },
	'l': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('l') },
	'b': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('b') },
	'n': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('n') },
	'm': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('m') },
	
	'alt+g': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+g') },
	'alt+h': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+h') },
	'alt+j': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+j') },
	'alt+k': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+k') },
	'alt+l': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+l') },
	'alt+b': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+b') },
	'alt+n': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+n') },
	'alt+m': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+m') },
	//
	'f1': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('f1') }  ,
	'f2': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('f2') }  ,
	'f3': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('f3') }  ,
	'f4': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('f4') }  ,
	'f5': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('f5') }  ,
	'f6': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('f6') }  ,
	'f7': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('f7') }  ,
	'f8': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('f8') }  ,
	'f9': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('f9') }  ,
	'f10': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('f10') },
	'f11': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('f11') },
	'f12': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('f12') },
	
	'alt+f1': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+f1') }  ,
	'alt+f2': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+f2') }  ,
	'alt+f3': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+f3') }  ,
	'alt+f4': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+f4') }  ,
	'alt+f5': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+f5') }  ,
	'alt+f6': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+f6') }  ,
	'alt+f7': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+f7') }  ,
	'alt+f8': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+f8') }  ,
	'alt+f9': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+f9') }  ,
	'alt+f10': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+f10') },
	'alt+f11': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+f11') },
	'alt+f12': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+f12') },
	//
	'd': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pasteLastPreset('end') },
	'ctrl+v': function(a) { a.preventDefault ? a.preventDefault() : a.returnValue = !1;  pastePreset('alt+f12') },
});

$('input#brandsearch').keyup(function() {
	// dehighlightAllObj();
	$('#brands li').removeClass('offsearch'); //first clear prev search
	$('#brands li ul li').each( function(){
		if ( ( $(this)[0].innerText ).toLowerCase().indexOf( $('input#brandsearch').val() ) < 0 ) $(this).addClass('offsearch')
	})
})
$("#brandsearchclear").click(function(){
    $("#brandsearch").val('');
	$('#brands li').removeClass('offsearch'); //first clear prev search
});
$('input#tpointsearch').keyup(function() {
	// dehighlightAllObj();
	$('#tpoints li').removeClass('offsearch'); //first clear prev search
	$('#tpoints li').each( function(){
		if ( ( $(this)[0].innerText ).toLowerCase().indexOf( $('input#tpointsearch').val() ) < 0 ) $(this).addClass('offsearch')
	})
})
$("#tpointsearchclear").click(function(){
    $("#tpointsearch").val('');
	$('#tpoints li').removeClass('offsearch'); //first clear prev search
});
$( "#hits" ).change(function() {
	$('input#tpointsearch, input#brandsearch').val("")
	$('#brands li, #tpoints li').removeClass('offsearch');
})

var currentMousePos = { x: -1, y: -1 };
$(document).mousemove(function(event) {
	currentMousePos.x = event.pageX;
	currentMousePos.y = event.pageY;
});
	
$(window).bind('mousewheel', function(e){
	if ( 1 == highlighted.length 
		&& $('#box').position().left < currentMousePos.x
		&& currentMousePos.x < $('#box').position().left + $('#box').width()
		&& currentMousePos.y > $('#box').position().top
		&& currentMousePos.y < $('#box').position().top + $('#box').height()
		&& !e.ctrlKey
	) {
		//HITS
		e.preventDefault();
		if ( isKeyPressed(e)==0 ) {
			if (e.originalEvent.wheelDelta > 0 && document.getElementById("hits").value < 15) {
				a = highlighted;
				var b = $("#brands ul li.selected").attr('id'),
					c = $("#tpoints ul li.selected").text(),
					d = $("#hits").val();
				if ("" == d) return alert("Please select again the hits number."), document.getElementById("hits").selectedIndex = -1, !1;
				if ("" != b && "" != c) {
					for ( var e = 0, g = a.length; e < g; e++ ){ 
						a[e].annotation.group = b.split("__")[0], 
						a[e].annotation.brand = b.split("__")[1], 
						a[e].annotation.tpoint = c, 
						a[e].annotation.hits = parseInt(d, 10)+1, 
						nullAnnoFlag--;
					}
				}
				$('#hits').val( parseInt(d, 10)+1 );
			}
			else if(e.originalEvent.wheelDelta < 0 && document.getElementById("hits").value > 1 ) {
				a = highlighted;
				var b = $("#brands ul li.selected").attr('id'),
					c = $("#tpoints ul li.selected").text(),
					d = document.getElementById("hits").value;
				if ("" == d) return alert("Please select again the hits number."), document.getElementById("hits").selectedIndex = -1, !1;
				if ("" != b && "" != c) {
					for ( var e = 0, g = a.length; e < g; e++ ){ 
						a[e].annotation.group = b.split("__")[0], 
						a[e].annotation.brand = b.split("__")[1],  
						a[e].annotation.tpoint = c, 
						a[e].annotation.hits = parseInt(d, 10)-1, 
						nullAnnoFlag--;
					}
				}
				$('#hits').val(parseInt(d, 10)-1);
			}
		}
		else if ( isKeyPressed(e)==1 ) {
			//TPOINTS
			if ( e.originalEvent.wheelDelta > 0 ) {
				a = highlighted;
				var curconn = $("#brands ul li.selected").attr('id'),
					cIndex = $("#tpoints .selected").index(),
					c = $("#tpoints ul li").eq(cIndex+1).text(),
					d = document.getElementById("hits").value;
				if ("" == d) return alert("Please select again the hits number."), document.getElementById("hits").selectedIndex = -1, !1;
				if ("" != curconn && "" != c) {
					for ( var e = 0, g = a.length; e < g; e++ ){ 
						a[e].annotation.group = curconn.split("__")[0], 
						a[e].annotation.brand = curconn.split("__")[1], 
						a[e].annotation.tpoint = c, 
						a[e].annotation.hits = parseInt(d, 10), 
						nullAnnoFlag--;
					}
				}
				if ( cIndex+1 < $("#tpoints ul li").length ) {	$("#tpoints ul li").eq(cIndex+1).addClass('selected')}
				else {	$("#tpoints ul li").eq(0).addClass('selected')	}
				$("#tpoints ul li").eq(cIndex).removeClass('selected')
			}
			else if( e.originalEvent.wheelDelta < 0 ) {
				a = highlighted;
				var b = $("#brands ul li.selected").attr('id'),
					cIndex = $("#tpoints .selected").index(),
					c = $("#tpoints ul li").eq(cIndex-1).text(),
					d = document.getElementById("hits").value;
				if ("" == d) return alert("Please select again the hits number."), document.getElementById("hits").selectedIndex = -1, !1;
				if ("" != b && "" != c) {
					for ( e = 0; e < a.length; e++ ){ 
						a[e].annotation.group = b.split("__")[0], 
						a[e].annotation.brand = b.split("__")[1], 
						a[e].annotation.tpoint = c, 
						a[e].annotation.hits = parseInt(d, 10), 
						nullAnnoFlag--;
					}
				}
				if ( cIndex > 0 ) {	$("#tpoints ul li").eq(cIndex-1).addClass('selected')}
				else {	$("#tpoints ul li").eq( $("#tpoints ul li").length-1 ).addClass('selected')	}
				$("#tpoints ul li").eq(cIndex).removeClass('selected')
			}
		}
	}
	if ( e.ctrlKey && highlighted.length>0 ) {	//	resize blocks
		
		a = highlighted;
		for ( var e = 0; e < a.length; e++ ){ 
			// alert(a[e].annotation.brand)
			// e.preventDefault;
			// a[e].annotation.group = b.split("__")[0], 
			// a[e].annotation.brand = b.split("__")[1], 
			// a[e].annotation.tpoint = c, 
			// a[e].annotation.hits = parseInt(d, 10)+1, 
			// nullAnnoFlag--;
		}
	}
});

function brandScrollTo() {
	var container = $('#brands'),	elem = $('#brands li ul li.selected');
	//	container.offset() einai stathero {top: 208, left: 1110}
	var elemtotop = elem.offset()
	container.animate({
		scrollTop: elemtotop.top - container.offset().top + container.scrollTop()-20
	}, 50);
}

/////////	TYPING CONTROL
var typingTimer, chartyped = '' ;
$(document).on('keydown', function(e) {
	if( $("#brands").css('background-color')=="rgba(255, 255, 255, 0)" ){	//an to mouseover einai sto brand list
		Mousetrap.pause();
		var keystr = String.fromCharCode(e.which);
		if (typingTimer) { chartyped += keystr;} else { chartyped = keystr; }
		var regex = new RegExp('^' + chartyped, 'i');
		if ( $('#brands li ul li').filter( function(){ return regex.test($(this).text()) ; } ).length>0 )
		
		if ( $('#brands li ul li.selected').nextAll().filter( function(){ return regex.test($(this).text()) } ).length>0 ){	// an yparxei sto idio group
			$('#brands li ul')
				.find('li.selected')
				.removeClass('selected')
				.nextAll()
				.filter( function(){
					return regex.test($(this).text());
				}).first().click().addClass('selected');
			brandScrollTo();
		}else if ( $('#brands li ul li.selected').parent().parent().nextAll('li').length>0 ) {	//// an uparxei epomeno group tote
			var nextAll = $('#brands li ul li.selected').parent().parent().nextAll('li').find('ul li')
			$('#brands li ul li.selected').removeClass('selected')
			nextAll.filter( function(){
					return regex.test($(this).text());
				}).first().click().addClass('selected');
			brandScrollTo();
		}else{
			$('#brands li ul li').removeClass('selected').filter( function(){
				return regex.test($(this).text());
			}).first().click().addClass('selected');
			brandScrollTo();					
		}
	}else{
		if ("" !== document.getElementById("projectFolder").value) {
			Mousetrap.unpause();
		}
	}
	typingTimer = setTimeout( function() { chartyped = '';	typingTimer = undefined; }, 500 )
})

