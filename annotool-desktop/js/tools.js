$('.toolbar button').attr('disabled','true');

//// TOOLS BUTTON
$('a#jpgsave').on( 'click',  function(e) { e.preventDefault(); dlimg(); return false; } );

var cJPG = document.getElementById('copyjpg');
cJPG.onclick = toClipboard;
var vpre = document.getElementById('vpresets');
vpre.onclick = vPresets;

$(function() {
	$("a[rel*=leanModal]").leanModal({ top : 100, closeButton: ".modal_close" });	
});

//// 	PREVIEW		////
function preview() {
	$('#preview .horizontal-slide').html("")
	
	var files=[];
	var start=0, end=10; //an uparxoun oi 5 prin kai 5 meta photo
	imIndex + start < 0 ? start = -imIndex : start = start;	// an den uparxoun oi 5 prin
	imIndex + end > imIndices.length ? end = imIndices.length-imIndex : end = end ;	// an den uparxoun oi 5 meta
	
	for (var i = start; i < end; i++) {
		var newImName = imIndices[ imIndex + i ]
		files.push( imAll[ newImName ] )
	}
	$('#preview .horizontal-slide').hide()
	var reader = new FileReader();  
	function readFile(index) {
		if( index >= files.length ) { thumbsClick(); return; }
		if ( files[index] ){
			var file = files[index];
			reader.onload = function(e) {
				var bin = e.target.result;
				if (index==0){
					$('#preview .horizontal-slide').append('<li class="col-md-2 prevthumbs"><span><b>'+file.name.split(".")[0]+'</b></span><img class="thumbnail" src="'+bin+'"></li>')
				}else{
					$('#preview .horizontal-slide').append('<li class="col-md-2 prevthumbs"><span>'+file.name.split(".")[0]+'</span><img class="thumbnail" src="'+bin+'"></li>')
				}
				readFile(index+1)
			}
			reader.readAsDataURL(file);
		}
	}
	readFile(0);
	reader.onloadend = function() {
		$('#preview .horizontal-slide').fadeIn( 'fast' )

	}
}

function thumbsClick(){
	$("li.prevthumbs").click( function() {
		loadImg ( imIndices.indexOf( $(this).find("span").eq(0).text() ) )
	});
}

//// 	VIEW PRESETS	////
function vPresets() {
	$('#viewpresets').html("");
	var keyslist = '<option>-NONE-</option>';
	for (var x in allAnnotations.presets) {
		if (allAnnotations.presets.hasOwnProperty(x)) {
			if (allAnnotations.presets[x].length>0){
			keyslist += '<option>'+x+'</option>';
				for (i=0;i<allAnnotations.presets[x].length; i++){			
					$('#viewpresets').append( "<div><b>"+x+"</b>"+" : "+allAnnotations.presets[x][i].annotation.brand+" - "+allAnnotations.presets[x][i].annotation.tpoint+" - "+allAnnotations.presets[x][i].annotation.hits+"</div>" );
				}
			}
			else{
				$('#viewpresets').append( "<b>"+x+"</b>"+" : <mark>empty</mark><br>" );
			}
		}
	}
	$('#viewpresets').prepend( '<div id="presetkeys"><select size="25">'+keyslist+'</select></div>' );
	// $("#presetkeys").val("-NONE-");
}

$(document.body).on('change','#presetkeys select',function(){
	if( $( "#presetkeys select option:selected" ).text() == '-NONE-' ){
		lockedpreset = "";
	}else{
		lockedpreset = $( "#presetkeys select option:selected" ).text();
	}
});
//// 	VIEW PRESETS END	////		

//// 	TOOLS	////		
////	image tools
function toClipboard() { 
	var x = document.getElementById('frame')
	x.getElementsByTagName('img')[0].innerHTML="";	
	var svg=document.getElementsByTagName("svg")[0];
	var box=document.getElementById('box');
	var boxWidth=box.style.width;
	var boxHeight=box.style.height;

	if(svg){
		svg.setAttribute('width', boxWidth);
		svg.setAttribute('height', boxHeight);

		html2canvas([ svg ], {
			onrendered: function(canvas) {
				var data = canvas.toDataURL('image/jpeg');
				x.getElementsByTagName('img')[0].setAttribute("src", data);
			}
		});
		var finalname = "#" + $("#brands li.selected").text() + " <br> " + $("#tpoints li.selected").text();
		document.getElementById("framename").innerHTML = finalname;
	}
}

function dlimg() {
	document.getElementById('jpgsave').blur();
	var svg=document.getElementsByTagName("svg")[0];
	if(svg){
		var box=document.getElementById('box');
		var boxWidth=box.style.width;
		var boxHeight=box.style.height;

		svg.setAttribute('width', boxWidth);
		svg.setAttribute('height', boxHeight);

		console.log(svg, boxWidth, boxHeight);

		html2canvas(document.getElementById('box'), {
				width: boxWidth,
				height: boxHeight
			})
			.then(function (canvas) {
				var data = canvas.toDataURL('image/jpeg');
				var image = new Image();
				image.src = data;
				var finalname = $("#brands .selected").text() + " - " + $("#tpoints .selected").text()+".jpg";
				saveJPG(data, finalname.replace(/ - /g,"-"));
			})
			.catch(function (err) { console.log(err); });
	}
}
 
function saveJPG(uri, filename) {
	var link = document.createElement('a');
	if (typeof link.download === 'string') {
		link.href = uri;
		link.download = filename;
		document.body.appendChild(link);	//Firefox requires the link to be in the body
		link.click();	//simulate click
		document.body.removeChild(link);	//remove the link when done
	} 
	else {
		window.open(uri);
	}
}

$('button#seelater').click(function() {		//DONE
	var a = imIndices.indexOf ( allAnnotations.currentImage ) ;
	if ( jQuery.inArray( a, prefs.seelater )<0 ) {	
		prefs.seelater.push(a); 
		$('select#laterlist').append( $('<option></option>').attr('value' , a ).html( imIndices[a]) )
		new Noty({ type: 'success', theme: 'mint', layout: 'bottomRight',  text: 'η εικόνα προσθέθηκε στη λίστα',  progressBar: false, timeout: 1000 }).show()
	}else{
		new Noty({ type: 'warning', theme: 'mint', layout: 'bottomRight',  text: 'είναι ήδη στη λίστα',  progressBar: false, timeout: 1000 }).show()
	}
	if ( $("#laterdiv").css('display')=="none" ) { $("#laterdiv").show() }
})

$("#btn_tpfltr").click(function() {
	if( $("#tpfltr").css('display')=="none" && ! $.fn.DataTable.isDataTable( '#tbl_tpfltr' ) ){
		tpfltrdata()
	}
	$("#tpfltr").slideToggle( 'fast' , 'swing' )
});

$("#colorsedit").click(function() {
	// if( $("#colorseditpanel").css('display')=="none" && ! $.fn.DataTable.isDataTable( '#tbl_tpfltr' ) ){
		// tpfltrdata()
	// }
	$("#colorseditpanel").slideToggle( 'fast' , 'swing' )
	
	$('#colorseditpanel #col2 canvas').css( 'border-color', boxborder );
	$('#colorseditpanel #col2 canvas').css( 'border-width', boxborderwidth );
	$('#colorseditpanel #col3 canvas').css( 'border-color', highlightstrokecolor );
	$('#colorseditpanel #col3 canvas').css( 'border-width', highlightstrokecolorwidth );
});

$("#annofilters").click(function() {
	if( $('#projectFolder').val() !== "" ){
		$("#annos").slideToggle( 'fast' , 'swing' )
	}
	else {
		new Noty({ type: 'error', theme: 'mint', layout: 'topRight',  text: 'please load images',  timeout: 1000,  closeWith: ['click', 'button'],}).show();
	}
});

$("#prevthumbs").click(function() {
	if( $('#preview').hasClass('hidden') ){
		$('#preview').removeClass('hidden')
		preview()
		prevopen=true;
	}
	else {
		$('#preview .horizontal-slide').html("")
		$('#preview').addClass('hidden')
		prevopen=false;
	}
});

///////		EDIT LISTS FUNSTIONS
var listedited=0;
$('button#addbrand').click(function() {	//DONE
	if ( $("#brands .brand").length>0 ) {
		if( $("#brands li.selected").length==0 ) {
			$("#brands>ul>li:first-child>ul>li:first-child").after('<input id="newbrand" type="text">') 
			var curgroup = $("#brands ul li ul li:first-child").attr('id').split('__')[0];
		} else {
			$("#brands li.selected").after('<input id="newbrand" type="text">') ;
			var curgroup = $("#brands li.selected").attr('id').split('__')[0];
			$("#brands li.selected").removeClass('selected');
		}
	}else{
		$("#brands li ul").append('<input id="newbrand" type="text">') ;
		var curgroup = $("#brands li").attr('id');
	}	
		
		$('input#newbrand').focus();
		
		var $_searchQuery = $('input#newbrand');
		$_searchQuery.autocomplete({
			source: prefs.brands
		});
		
		$("input#newbrand").on('focusout', function () {
			if( $('input#newbrand').val().trim() !== "" ){
				var added = $('input#newbrand').val().trim();
				var newconn = curgroup+"__"+added;
				$("input#newbrand").after( $('<li></li>').attr('id',newconn).attr('value',added).text( added ) ) ;   
				$("#brands li.selected").removeClass('selected');
				$('#brands li').each( function(){
					if( $(this).attr('id') == newconn ){
						$(this).addClass("selected");
						$(this).addClass("ui-sortable-handle");
					}
				} )
				prefs.conns[newconn] = { group:curgroup, brand:added, tpoints : [] }
				prefs.userAdds[newconn] = { group:curgroup, brand:added, tpoints : [] }
				$("input#newbrand").next().addClass("selected")
				$("input#newbrand").next().addClass("ui-sortable-handle");
				$("input#newbrand").remove();
				brandsInit();
				fillTouchpoints(newconn)
			}else{
				$("input#newbrand").remove();
			}
		});
listedited++;
})

$('button#delbrand').click(function() {		//DONE
	if( $("#brands li.selected").length>0 ){
		var del = $("#brands li.selected").text();
		var conn = $("#brands li.selected").attr('id');
		var n = new Noty({
			type: 'warning',
			theme: 'mint',
			text: 'delete "'+del+'" ?',
			buttons: [
				Noty.button('YES', 'btn btn-success', function () {
					$("#brands li.selected").remove();
					$("#tpoints ul").remove();
					delete prefs.conns[conn];
					n.close();
				}, {id: 'button1', 'data-status': 'ok'}),

				Noty.button('NO', 'btn btn-error', function () {
					n.close();
				})
			]
		}).show();
	}
listedited++;
})

$('button#editbrand').click(function() {	//DONE	
	if ( $("#brands li.selected").length>0 ) {
		var that = $(this);
		$(this).addClass('clicked');
		if( $('.toolbar button:disabled').length==0 ){
			$('.toolbar button').attr('disabled','true');
			$(this).removeAttr('disabled');
		}
			var curbrand = $("#brands li.selected").text();
			var curconn = $("#brands li.selected").attr('id');
			$("#brands li.selected").after('<input id="newbrand" type="text">');
			$('input#newbrand').val( curbrand );
			$("#brands li.selected").remove();
			$('input#newbrand').focus();
			
			var $_searchQuery = $('input#newbrand');
			$_searchQuery.autocomplete({
				source: prefs.brands
			});
			
			$("input#newbrand").on('focusout', function () {
				that.removeClass('clicked');
				$('.toolbar button').attr('disabled','true');
				$('.toolbar button').removeAttr('disabled');
				
				if( $('input#newbrand').val().trim() == ""  || $('input#newbrand').val() == curbrand ){
					var edited = curbrand;
					var newconn = curconn.split('__')[0]+"__"+edited;
				} else {
					var edited = $('input#newbrand').val().trim();	
					var newconn = curconn.split('__')[0]+"__"+edited;
					prefs.conns[newconn] = { group:prefs.conns[curconn].group, brand:edited, tpoints : prefs.conns[curconn].tpoints }
					delete prefs.conns[curconn];	
				}
				$("input#newbrand").after( $('<li></li>').attr('id',newconn).attr('value',edited).text( edited ) ) ;    
				$("input#newbrand").remove();
				$("#brands li.selected").removeClass('selected');
				$('#brands li').each( function(){
					if( $(this).attr('id') == newconn ){
						$(this).addClass("selected");
						$(this).addClass("ui-sortable-handle");
					}
				})
				brandsInit();
			});	
			$("input#newbrand").on('keyup', function (e) {
				if (e.keyCode == 13) {
					$("input#newbrand").focusout()
				}
			});
			listedited++;	
		
	}

})

$('button#togglegroups').click(function() {	//done
	$(this).toggleClass('clicked');
	if( $('.toolbar button:disabled').length>0 ){
		$('#brands li.group i').remove();
		$('.toolbar button').attr('disabled','true');
		$('.toolbar button').removeAttr('disabled');
		$('#i_all').remove();
	}else{
		$('#brandstools').after( '<div id="i_all"><i class="fa fa-chevron-circle-left"></i><i class="fa fa-chevron-circle-down"></i></div>' )
		$('#i_all i.fa-chevron-circle-left').on( 'click', function() {
			$('#brands li.group ul').slideUp('fast');
			$('#brands li.group i').attr('class',"fa fa-chevron-circle-left");
			$('#brands li.group').addClass('minimized');
		});
		$('#i_all i.fa-chevron-circle-down').click( function() {
			$('#brands li.group ul').slideDown('fast');
			$('#brands li.group i').attr('class',"fa fa-chevron-circle-down")
			$('#brands li.group').removeClass('minimized');
		})
		$('#brands li.group>ul').each(function(){
			if( $(this).css('display')=="none" ) {
				$(this).parent().append('<i class="fa fa-chevron-circle-left"></i>');
			}else{
				$(this).parent().append('<i class="fa fa-chevron-circle-down"></i>');
			}
		})
		$('.toolbar button').attr('disabled','true');
		$(this).removeAttr('disabled');
	}
	$('#brands li.group i').click( function() {
		if( $(this).parent().find('ul').is(':visible') ){ 
			$(this).parent().find('ul').slideToggle('fast');
			$(this).attr('class',"fa fa-chevron-circle-left")
			$(this).parent().addClass('minimized');
		} else {
			$(this).parent().find('ul').slideToggle('fast');
			$(this).attr('class',"fa fa-chevron-circle-down")
			$(this).parent().removeClass('minimized');
		}
	});
listedited++;
})

$('button#sortbrands').click(function() { //done
	$(this).toggleClass('clicked');
	$('#brands ul').toggleClass("sortable");
	if ($('#brands ul').sortable("option" ,"disabled")){
		$('#brands ul').sortable("enable");  
		$('.toolbar button').attr('disabled','true');
		$(this).removeAttr('disabled');
	}else{
		$('#brands ul').sortable('disable');
		$('.toolbar button').attr('disabled','true');
		$('.toolbar button').removeAttr('disabled');
	}
listedited++;
});

$('button#sorttpoints').click(function() { 	//done
	$(this).toggleClass('clicked');
	$('#tpoints ul').toggleClass("sortable");
	if ($('#tpoints ul').sortable("option" ,"disabled")){
		$('#tpoints ul').sortable("enable");  
		$('.toolbar button').attr('disabled','true');
		$(this).removeAttr('disabled');
		
	}else{
		var arr = [];
		$("#tpoints ul li").each(function() { arr.push($(this).text()) });
		prefs.conns[$("#brands li.selected").attr('id')].tpoints = arr;
		$('#tpoints ul').sortable('disable');
		$('.toolbar button').attr('disabled','true');
		$('.toolbar button').removeAttr('disabled');
	}
listedited++;
});

$('button#addtpoint').click(function() { 	//done
	if ( $("#brands li.selected").length==1 ) { //activate ONLY when a brand selected
		// if selected brand has NO tpoints ? add the first one, else : if NO tpoint is selected ? insert on top, else : insert after selected
		var beforeindex;
		if ( $("#tpoints li.selected").length==0 || $("#tpoints li").length==0 ){ 
			$("#tpoints ul").prepend('<input id="newtpoint" class="typeahead" type="text">')
			beforeindex = 0
		}else{
			$("#tpoints li.selected").after('<input id="newtpoint" class="typeahead" type="text">');
			beforeindex = $("#tpoints li.selected").index()
		}
		$('input#newtpoint').focus();
		
		var $_searchQuery = $('input#newtpoint');
		$_searchQuery.autocomplete({
			source: prefs.tpoints
		});
		
		$("#tpoints li.selected").removeClass('selected');
		
		$("input#newtpoint").on('focusout', function () {
			if( $('input#newtpoint').val().trim() !== "" ){
				var thisconn = $("#brands li.selected").attr('id');
				var added = $('input#newtpoint').val().trim();
				$("input#newtpoint").after('<li id="'+$('input#newtpoint').val()+'">'+$('input#newtpoint').val()+'</li>');    
				$("#tpoints li").removeClass('selected');
				
				if ( jQuery.inArray( added, prefs.tpoints )<0 ){
					prefs.tpoints.push( added );
					prefs.tpoints.splice( beforeindex, 0, added );
				}
				// prefs.conns[ thisconn ].tpoints.push( added );
				prefs.conns[ thisconn ].tpoints.splice( beforeindex+1, 0, added );
				
				if ( prefs.userAdds.hasOwnProperty(thisconn) ) {	//an exei prostethei to brand ap to xristi kai epomenos uparxei idi sta userAdds
					prefs.userAdds[ thisconn ].tpoints.push(added)
				}
				else{
					prefs.userAdds[ thisconn ] = new Object();
					prefs.userAdds[ thisconn ].tpoints = [added]
					prefs.userAdds[ thisconn ].group = prefs.conns[ thisconn ].group
					prefs.userAdds[ thisconn ].brand = prefs.conns[ thisconn ].brand
				}
			}else{
				$("input#newtpoint").remove();
			}
			$("input#newtpoint").next().addClass("selected")
			$("input#newtpoint").next().addClass("ui-sortable-handle");
			$("input#newtpoint").remove();
			tpointsInit();
		});
		$("input#newtpoint").on('keyup', function (e) {
			if (e.keyCode == 13) {
				$("input#newtpoint").focusout()
			}
		});
	}
	listedited++ ;
})

$('button#deltpoint').click(function() {	//done
	if( $("#tpoints li.selected").length>0 ){
		var del = $("#tpoints li.selected").text()
	
		var n = new Noty({
			type: 'warning',
			theme: 'mint',
			text: 'delete "'+del+'" ?',
			buttons: [
				Noty.button('YES', 'btn btn-success', function () {
					$("#tpoints li.selected").remove();
					var thisconn = $("#brands li.selected").attr('id') ;
					var index = prefs.conns[ thisconn ].tpoints.indexOf(del)
					prefs.conns[ thisconn ].tpoints.splice(index,1);	//delete from conn tpoints
					if ( prefs.userAdds.hasOwnProperty(thisconn) ) {
						var index = prefs.userAdds[ thisconn ].tpoints.indexOf(del)
						prefs.userAdds[ thisconn ].tpoints.splice(index,1);
					}
					n.close();
				}, {id: 'button1', 'data-status': 'ok'}),

				Noty.button('NO', 'btn btn-error', function () {
					n.close();
				})
			]
		}).show();
	}
	listedited++;
})

$('button#edittpoint').click(function() {
	if ( $("#tpoints li.selected").length>0 ){
		var that = $(this);
		$(this).addClass('clicked');
		if( $('.toolbar button:disabled').length==0 ){
			$('.toolbar button').attr('disabled','true');
			$(this).removeAttr('disabled');
		}
		
		var current = $("#tpoints li.selected").text();
		$("#tpoints li.selected").after('<input id="newtpoint" type="text">');
		$('input#newtpoint').val( current );
		$('input#newtpoint').focus();
		$("#tpoints li.selected").remove();
		
		var $_searchQuery = $('input#newtpoint');
		$_searchQuery.autocomplete({
			source: prefs.tpoints
		});
		$("input#newtpoint").on('focusout', function () {
			that.removeClass('clicked');
			$('.toolbar button').attr('disabled','true');
			$('.toolbar button').removeAttr('disabled');
			
			if( $('input#newtpoint').val().trim() !== "" ){
				var added = $('input#newtpoint').val().trim();
				$("input#newtpoint").after( $('<li></li>').attr( 'id',added ).text( added ) );    
				var index = prefs.conns[$("#brands li.selected").attr('id')].tpoints.indexOf(current);
				prefs.conns[$("#brands li.selected").attr('id')].tpoints[index] = added;
			}else{
				$("input#newtpoint").after( $('<li></li>').attr( 'id',current ).text( current ) );    
				$("#tpoints li.selected").removeClass('selected');
			}
			$("input#newtpoint").next().addClass("selected");
			$("input#newtpoint").next().addClass("ui-sortable-handle");
			$("input#newtpoint").remove();
			tpointsInit();
		});
		$("input#newtpoint").on('keyup', function (e) {
			if (e.keyCode == 13) {
				$("input#newtpoint").focusout()
			}
		});
		listedited++;
	}
})

function tpointsAbc(){		//done
	var items = $('#tpoints li').get();
	items.sort(function(a,b){
	  var keyA = $(a).text();
	  var keyB = $(b).text();

	  if (keyA < keyB) return -1;
	  if (keyA > keyB) return 1;
	  return 0;
	});
	var ul = $('#tpoints ul');
	$.each(items, function(i, li){
	  ul.append(li); /* This removes li from the old spot and moves it */
	});
}

function tpointsFreq(){		//done
	var brand = $("#brands li.selected");
	var group = brand.parent().parent().attr('id')
	annokeys=Object.keys(commonExportData());	// annokey = px: "34::ECB::Adidas::Bib"
	
	if ( $("#brands li.selected").length >0 && annokeys.length >0 ) {	//IF A BRAND IS SELECTED && THERE ARE ANNOTATIONS
		var thisarr = {};
		for( i=0; i<annokeys.length; i++ ){
			if ( annokeys[i].indexOf( group+"::"+brand.text() )>-1 ) {
				var tp = annokeys[i].split("::")[3]
				if ( tp in thisarr  ) {
					thisarr[ tp ]++
				}else{
					thisarr[ tp ]=1
				}
			}
		}
		var sortable=[];
		for(var key in thisarr){
			if(thisarr.hasOwnProperty(key))
				sortable.push( thisarr[key]+"__"+key ); 
		}
		for( i=0; i<sortable.length; i++ ){
			var it = sortable[i].split("__")[1]
			$("#tpoints ul li").each(function(){
				if ($(this).text()==it) $(this).insertBefore($("#tpoints ul li").eq(0) );
			})			
		}
		var arr = [];
		$("#tpoints ul li").each(function() { arr.push($(this).text()) });
		prefs.conns[$("#brands li.selected").attr('id')].tpoints = arr;
	}
}

function newTxt(){		//done
	if( $('#brands li').length > 0 ){
		var a = "//Filename:"+prefs.projectName+"\r\n//Annotator:"+prefs.AnnotatorName+"\r\n";
		var group;
		for( i=0; i<$('#brands li.group').length; i++ ){
			a += "\r\n--  "+ $('#brands li.group')[i].id+"\r\n";
			var childs = $('#brands li.group').eq(i).children('ul').children('li')
			for( j=0; j<childs.length; j++ ){
				a +=  "\r\n#"+childs[j].id.split("__")[1]+"\r\n";
				a += prefs.conns[ childs[j].id ].tpoints.join('\r\n')+'\r\n' ;
			}
		}
		a = new Blob([a], {type: "text/plain;charset=utf-8"});
		saveAs(a, allAnnotations.project.replace(/ /g,'_').replace(/---|--/g,'-') + "-" + allAnnotations.Annotator + "-" + timestamp() + ".txt");
	}
listedited=0;
}

function sort_table(tbody, col, asc){
	var rows = tbody.rows, rlen = rows.length, arr = new Array(), i, j, cells, clen;
	// fill the array with values from the table
	for(i = 0; i < rlen; i++){
	cells = rows[i].cells;
	clen = cells.length;
	arr[i] = new Array();
		for(j = 0; j < clen; j++){
		arr[i][j] = cells[j].innerHTML;
		}
	}
	// sort the array by the specified column number (col) and order (asc)
	arr.sort(function(a, b){
		return (a[col] == b[col]) ? 0 : ((a[col] > b[col]) ? asc : -1*asc);
	});
	for(i = 0; i < rlen; i++){
		arr[i] = "<td>"+arr[i].join("</td><td>")+"</td>";
	}
	tbody.innerHTML = "<tr>"+arr.join("</tr><tr>")+"</tr>";
}

function GetCheckedState (input) {	//not used
	//var input = document.getElementById ("myInput");
	var isChecked = input.checked;
	isChecked = (isChecked)? 1 : 0;
	return (isChecked);
}

////////		LATER LIST
function later_Prev() {
	if ( $('#imageName').val()!=="" && prefs.seelater.length>0 ){
	document.getElementById("later_prev").blur();
		var curindex = imIndices.indexOf( allAnnotations.currentImage );
		var index = prefs.seelater.indexOf( curindex )
		if ( prefs.seelater.indexOf( curindex ) == -1 ) {	//an den einai meros tis listas bres to kontinotero
			var closest = null;
			$.each(prefs.seelater, function(){
				if (closest == null || Math.abs(this - curindex) < Math.abs(closest - curindex)) {
					closest = this;
				}
			});
			$('select#laterlist').val(closest)
			loadImg( closest )
			
		}else if( prefs.seelater.indexOf( curindex ) > -1 &&  index > 0 ){	//an einai meros tis listas pigaine sto proigoumeno
			if (imReadFlag) return !1;
			imReadFlag = !0;
				loadImg( prefs.seelater[ index-1 ] )
				$('select#laterlist').val( prefs.seelater[ index-1 ] )
		}
	}
}

function later_Next(){
	if ( $('#imageName').val()!=="" && prefs.seelater.length>0 ){
		document.getElementById("later_next").blur();
		var curindex = imIndices.indexOf( allAnnotations.currentImage );
		var index = prefs.seelater.indexOf( curindex )
		if ( prefs.seelater.indexOf( curindex ) == -1 ) {	//an den einai meros tis listas bres to kontinotero
			var closest = null;
			$.each(prefs.seelater, function(){
				if (closest == null || Math.abs(this - curindex) < Math.abs(closest - curindex)) {
					closest = this;
				}
			});
			$('select#laterlist').val(closest)
			loadImg( closest )
			
		}else if( prefs.seelater.indexOf( curindex ) > -1 &&  index+1 <  prefs.seelater.length ){	//an einai meros tis listas pigaine sto proigoumeno
			if (imReadFlag) return !1;
			imReadFlag = !0;
				loadImg( prefs.seelater[ index+1 ] )
				$('select#laterlist').val( prefs.seelater[ index+1 ] )
		}
	}
}

function later_Img(a) {
	document.getElementById("later_next").blur();
	if ( $('#imageName').val()!=="" && prefs.seelater.length>0 ){
		if (imReadFlag) return !1;
		imReadFlag = !0;
		loadImg( a )
	}
}

$('button#laterlist').click( function(){
	$( 'span#laterlist' ).fadeToggle('fast');
	$('select#laterlist').html("")
	for (i in prefs.seelater){
		$('select#laterlist').append( $('<option></option>').attr('value' , prefs.seelater[i] ).html( imIndices[prefs.seelater[i]] ) )
	}
	$('select#laterlist').change( function(){
		later_Img( $(this).val() )
	})
})

//FOR AUTOCOMPLETE
$.ui.autocomplete.prototype._renderItem = function (ul, item) {
	var re = new RegExp($.trim(this.term.toLowerCase()));
	var t = item.label.replace(re, "<span style='font-weight:600;color:#5C5C5C;'>" + $.trim(this.term.toLowerCase()) +
		"</span>");
	return $("<li></li>")
		.data("item.autocomplete", item)
		.append("<a>" + t + "</a>")
		.appendTo(ul);
};

