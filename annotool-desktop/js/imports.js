//// TOP PANEL TOOLS
$("#workspace").change( function () {	//photo checkbox
	if ( $('#workspace').val() == "Photos" ) {
		$('#title-prefs label').css('display','inline-block')
		$('#howmanyleft').text( "left : "+( imIndices.length-imIndex ) )
		setInterval(function() {
			$('#howmanyleft').text( "left : "+( imIndices.length-imIndex ) )
		}, 60 * 100); // 60 * 1000 milsec

	}
	else { 
		$('#title-prefs label').css('display','none') 
		$('#howmanyleft').text("")
	}
})

function changeCss(){
	a = workspaceInput.options[workspaceInput.selectedIndex].text.toLowerCase();
	var b = "";
    "video" == a ? b = "css/video.css" : b = "css/photo.css" ;
    document.getElementById("workspace-css").setAttribute("href", b)
}

function loadPresetsFromJson() {
	var a = document.getElementById("loadPresets").files[0],
	b = new FileReader;
	b.onload = function(a) {
	a = JSON.parse(a.target.result);
		allAnnotations.prefs = a.prefs;
		for (var e in allAnnotations.presets) 0 == allAnnotations.presets[e].length &&
			(allAnnotations.presets[e] = a.presets[e])
    };
    b.onloadstart = function(a) {

    };
    b.onloadend = function(a) {
    
    };
    b.onerror = function(a) {
        console.error("Could not load the selected annotations file! Code " + a.target.error.code)
    };
    b.readAsText(a)
}

fileInput.addEventListener("change", function(a) {
    a = document.getElementById("projectFolderBox");
    if (0 === fileInput.files.length) return !1;
	
    var b = fileInput.files[0].webkitRelativePath.replace(/\\/g, "/"),
        b = b.substring(0, b.lastIndexOf("/") + 1);
    "" !== prefs.imgFoldername ? prefs.imgFoldername !== b ? (
		msg1 = "CAUTION: The folder you have selected is different than the one you ", 
		msg2 = " Are you sure you want to proceed ?", 
		confirm(msg1 + msg2) && (
			initJSXBoard(), 
			prefs.imgFoldername = b, 
			a.value = 0 < allAnnotations.imageNum ? "[" + allAnnotations.imageNum +
			" files]  " + b : "")) : 
			(initJSXBoard(), 
			a.value = 0 < allAnnotations.imageNum ? "[" + allAnnotations.imageNum + " files]  " + b : "") : 
			(initJSXBoard(), 
				0 < allAnnotations.imageNum && (prefs.imgFoldername = b, 
				a.value = "[" + allAnnotations.imageNum + " files]  " + b)
			);
	fileInput.blur();
	var optDiv = document.getElementById('workspace');
	var b,c = "";
	
	b = "css/video.css"; c=optDiv.getElementsByTagName('option')[0].value;	
	
	if ( $("#projectFolderBox").val().indexOf('images')>-1 ) {
		c = optDiv.getElementsByTagName('option')[1].value
		$('span#scrloc').css('display','inline-block')
		
		$('#howmanyleft').text( "left : "+( imIndices.length-imIndex ) )
		setInterval(function() {
			$('#howmanyleft').text( "left : "+( imIndices.length-imIndex ) )
		}, 60 * 100); // 60 * 1000 milsec
	}
	document.getElementById("workspace").value=c;
	changeCss();
	$(".topcol2, .topcol3, .topcol4").fadeIn() 
	$("#projectFolderBox").attr( 'title', $("#projectFolderBox").val() );
	$('.toolbar button').removeAttr('disabled');
	if ( prefs.seelater.length>0 ) { 
		$("#laterdiv").show() 
		$('button#laterlist').click()
	}
});

prefsInput.addEventListener("change", function(a) {
	if (prefsInput.value.length !== 0){
		readPrefsFile()
		prefsInput.blur()
	}
});


function readPrefsFile(a) {
    a = void 0 === a ? document.getElementById("projectPrefs").files[0] : a;
    if (void 0 === a || "" === a) return !1;
	
    var b = prefsInput.value.replace(/\\/g, "/").replace(/.*\//, "");
	if ( b.indexOf(".txt") == -1 ) {
		new Noty({  type: 'error', theme: 'mint', layout: 'top',  text: 'δε φόρτωσες αρχείο .txt',  timeout: 1000,  closeWith: ['click', 'button'],
					}).show();
		return !1;
	}
    prefs.prefsFilename = b;	//b = 2015-2016 A-League Round 5 Sydney v Brisbane_20151106_1850.txt
    document.getElementById("projectPrefsBox").value = b;	//b = 2015-2016 A-League Round 5 Sydney v Brisbane_20151106_1850.txt
	$("#projectPrefsBox").attr('title', b);
    prefs.conns = {};
	prefs.groups = [];
	prefs.brands = [];
	prefs.tpoints = [];
	
    b = new FileReader;
	b.onloadstart = function(a) {

	}	
	b.onprogress = function(a) {

	}
	b.onabort = function(a) {
		b.abort();
	}
    b.onerror = function(a) {
		var b = document.getElementById("workspace"),
        b = $("#brands ul li.selected").text().toLowerCase();
        console.error("Prefs file could not be read! Code " + a.target.error.code);
        alert("Error reading the preferences file. Make sure the file has the correct format.")
    }
    b.onload = function(a) {
		
	} 
    b.onloadend = function(a) {
		var lines = a.target.result.replace(/(?:\r\n|\r|\n)/g, '\n').split("\n");	//spaei se grammes
		globals = []; //global tpoints array
        var lastgroup, lastbrand;
		for ( i = 0; i < lines.length; i++ ){
			lines[i] = lines[i].replace(/\t+/g, "");
			if ( 0 == lines[i].indexOf("*") ){
				globals.push( lines[i].split("*")[1].trim() )
			}
			else if ( 0 == lines[i].indexOf("--") ) {	//an arxizei apo "--" 
				var arr = lines[i].split("--");
				if ( //an exei dilothei lathos to onoma
					arr[1].trim()=="" // an einai keno
					|| 0 == lines[i].indexOf("#--") // an einai me ton palio tropo
					|| 0 == lines[i].indexOf("---") // an exei 3 paules
					|| arr.length > 2 // an exei 4 paules kai pano 
				) {
					new Noty({ 
						type: 'error', theme: 'mint', layout: 'top',  text: 'δεν έχει δηλωθεί σωστά το γκρουπ, το σωστο είναι "--ΟΝΟΜΑ ΓΚΡΟΥΠ"',  timeout: 4000,  closeWith: ['click', 'button'],
					}).show();
					break;
				}else{
					lastgroup = lines[i].split("--")[1].trim();
				}
				prefs.groups.push( lastgroup )
			}
			else if (0 == lines[i].indexOf("//Filename:") ){
				f = lines[i].split("//Filename:")
				prefs.projectName = f[1].trim()
				document.getElementById("projectName").innerHTML = f[1].trim()
			}
			else if ( 0 == lines[i].indexOf("//Annotator:") ){
				f = lines[i].split("//Annotator:") 
				prefs.AnnotatorName = f[1].trim()
				document.getElementById("AnnotatorName").innerHTML = f[1].trim()
			}
			else if ( 0 == lines[i].indexOf("#") ){
				if ( 0 == lines[i].indexOf("#--") || 0 == lines[i].indexOf("#-") ) {
					new Noty({ 
						type: 'error', theme: 'mint', layout: 'top',  text: 'δεν έχει δηλωθεί σωστά το γκρουπ, το σωστο είναι "--ΟΝΟΜΑ ΓΚΡΟΥΠ"',  timeout: 4000,  closeWith: ['click', 'button'],
					}).show();
					break;
				}
				f = lines[i].split("")	//test
				f.shift()
				lastbrand = f.join("")
				if ( lastgroup == null ){ 	// an brei brand xoris group apo prin, diladi an den exei kanena (SOSTO) group
					new Noty({ 
						type: 'error', theme: 'mint', layout: 'top',  text: 'δεν έχει δηλωθεί κανένα γκρουπ',  timeout: 4000,  closeWith: ['click', 'button'],
					}).show();
					break;
				}
				prefs.conns[ ( prefs.groups[ prefs.groups.length-1 ]+"__"+lastbrand ).toString() ] = { brand:lastbrand, tpoints: [], group: prefs.groups[prefs.groups.length-1] }
			}
			else {
				if ( 0 == lines[i].indexOf("%") || lines[i].length<2 ){ 	//an einai sxolio
					continue 
				}
				prefs.conns[ lastgroup+"__"+lastbrand ].tpoints.push( lines[i].trim() )
				prefs.tpoints.push( lines[i].trim() )
			}			
		}
		var connssize = 0, key;
		for (key in prefs.conns) {
			if ( prefs.conns.hasOwnProperty(key) ){
				connssize++;
			}
		}
	//bazei ta global tpoints
		for (key in prefs.conns) {
			if ( prefs.conns.hasOwnProperty(key) ){
				prefs.conns[key].tpoints.splice.apply(prefs.conns[key].tpoints, [0, 0].concat(globals))
				prefs.tpoints.splice.apply(prefs.tpoints, [0, 0].concat(globals))
			}
		}
		b = $("#brands ul li");
		$("#brands").html("<ul></ul>");
	//bazei ta ul li
		for (i in prefs.groups) {
			$("#brands ul").append(
				$("<li></li>")
				.attr("id",prefs.groups[i])
				.attr("class","group")
				.attr("value",prefs.groups[i])
				.html("<h4>"+prefs.groups[i]+"</h4>")
			);
		}
		$("#brands ul li").append('<ul></ul>');
		for (key in prefs.conns) {
			if ( prefs.conns.hasOwnProperty(key) ){
				br = prefs.conns[key].brand;
				$("#brands ul li").each(function(){
					if( $(this).attr('id')==prefs.conns[key].group ){
						$('ul', this).append( $("<li></li>").attr("id",key).attr("value",br).text(br) ); 
					}
				})
			}
		}
		$( "#brands ul li ul li" ).each( function(){	
			prefs.brands.push( $( this ).text() ) // fill prefs.brands 
			var thisTp = ( prefs.conns[ $( this ).attr('id') ].tpoints );	//AND prefs.tpoints
			for ( i=0; i<thisTp.length; i++) {
				prefs.tpoints.push( thisTp[i] )
			}
		})
		prefs.brands = uniqueArr(prefs.brands)
		prefs.tpoints = uniqueArr(prefs.tpoints)
		disableGroups();
		resetGUIAnnoInfo();
		allAnnotations.project = prefs.projectName;
		allAnnotations.Annotator = prefs.AnnotatorName; //tassos
		allAnnotations.prefs = prefs;
		brandsInit();
		tpfltrdata()
		
		checkConnsChanges()
		$('#loadfiles').css('opacity','1')
    };
	b.readAsText(a);
}

newProjButton.addEventListener("click", function(a) {
    initProject();
    newProjButton.blur()
});

function initProject() {
    msg1 = "ΠΡΟΣΟΧΗ: η ενέργεια αυτή θα αδειάσει την προσωρινή μνήμη του Chrome";
    msg2 = "Aν δεν έχεις σώσει τη δουλειά σου σε json τα δεδομένα θα χαθούν";
	
    confirm(msg1 +"\n"+ msg2) && confirm("είσαι σίγουρος/η ;") && (clearInterval(autosaveTimer), 
    presets = {
		'f1':[], 'f2':[], 'f3': [], 'f4': [], 'f5':[], 'f6':[], 'f7':[], 'f8':[], 'f9':[], 'f10':[], 'f11':[], 'f12':[],
		'alt+f1':[], 'alt+f2':[], 'alt+f3': [], 'alt+f4': [], 'alt+f5':[], 'alt+f6':[], 'alt+f7':[], 'alt+f8':[], 'alt+f9':[], 'alt+f10':[], 'alt+f11':[], 'alt+f12':[],
        '1':[], '2':[], '3': [], '4': [], '5':[], '6':[], '7':[], '8':[], '9':[], '0':[],
        'alt+1':[], 'alt+2':[], 'alt+3': [], 'alt+4': [], 'alt+5':[], 'alt+6':[], 'alt+7':[], 'alt+8':[], 'alt+9':[], 'alt+0':[],
		'q':[], 'w':[], 'e':[], 'r':[], 't':[], 'y':[], 'u':[], 'i':[], 'o':[], 'p':[],	
		'alt+q':[], 'alt+w':[], 'alt+e':[], 'alt+r':[], 'alt+t':[], 'alt+y':[], 'alt+u':[], 'alt+i':[], 'alt+o':[], 'alt+p':[],	
		'g':[], 'h':[], 'j':[], 'k':[], 'l':[], 'b':[],	'n':[], 'm':[],	
		'alt+g':[], 'alt+h':[], 'alt+j':[], 'alt+k':[], 'alt+l':[], 'alt+b':[],	'alt+n':[], 'alt+m':[],	
		"end":[]
    },
	allAnnotations = {
        project: "",
        imageNum: "",
        prefs: {},
        images: {},
        currentImage: "",
        presets: presets
    },
	clearProjectPrefsSelection(), 
	clearProjectFolderSelection(), 
	localStorage.allAnnotations = "",
	$("#laterdiv").hide(),
	$(".topcol2, .topcol3, .topcol4").hide(),
	$('#loadfiles').css('opacity','0'),
	$('.toolbar button').attr('disabled','true'),	
	tpfltrdata(),
	$('.selector').hide()
	)
	
}