
// ALL Variables		
var 
im, 
imWidth, 
imHeight, 
imName, 
imIndex, 
prev_imName, 
prev_imIndex, 
next_imName, 
next_imIndex, 
brd, 
imList = [],
imAll = {},
imIndices = [],
imLength,
highlighted = [],
prefs = {
	projectName: "",
	AnnotatorName: "",
	prefsFilename: "",
	imgFoldername: "",
	userAdds: {},
	groups: [],
	brands: [],
	tpoints: [],
	conns: {},
	seelater: []
},
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
ctrlPressed = !1,
autosaveTimer, autosaveInterval = 60000,
imReadFlag = !1,
nullAnnoFlag = 0,
hasNull = 0,
lockedpreset = "",
prevopen = false,
fileInput = document.getElementById("projectFolder"),
newProjButton = document.getElementById("newProjButton"),
workspaceInput = document.getElementById("workspace"),
prefsRefresh = document.getElementById("prefsRefresh"),
prefsInput = document.getElementById("projectPrefs"),
loadAnn = document.getElementById("loadAnn"),
loadPresets = document.getElementById("loadPresets"),
// loadOpts = document.getElementById("loadOpts"),
imgNameInput = document.getElementById("imageName");
boxborder = "#4fe2ff",
boxborderwidth = 2,
highlightstrokecolor = "orange",
highlightstrokecolorwidth = 2,
mouseoverfillcolor = "white",
dotstrokecolor = "yellow";

window.onload = function() {
	Mousetrap.pause();
    checkLoadLocalStorage();
    for (var a = document.querySelectorAll('input[type="checkbox"].ios-switch'), b = 0, c; c = a[b++];) {
        var d = document.createElement("div");
        d.className = "switch";
        c.parentNode.insertBefore(d, c.nextSibling)
    }
};

window.onbeforeunload = function () {
    return "Have you downloaded the JSON file containing all the annotations?"
}

function showSpinner() {
    document.getElementById('myModal').style.display = "block";
}

function hideSpinner() {
    document.getElementById('myModal').style.display = "none";
}

//////// Event Listeners
workspaceInput.addEventListener("change", function(a) {
    a = workspaceInput.options[workspaceInput.selectedIndex].text.toLowerCase();
    var b = "";
    "video" == a ? b = "css/video.css" : b = "css/photo.css" ;
    document.getElementById("workspace-css").setAttribute("href", b)
});
$( "#hits" ).change(function(a) {
    a = highlighted;
    var b = $("#brands ul li.selected").attr('id'),   c = $("#tpoints ul li.selected").text(),   d = $("#hits").val();
    if ("" == d) return alert("Please select again the hits number."), document.getElementById("hits").selectedIndex = -1, !1;
    if ( b !== "" && c !== "" ) {
		if( a.length==0 ){
			new Noty({ type: 'error', theme: 'mint', layout: 'topRight',  text: 'δεν έχεις επιλέξει τετράγωνο',  timeout: 1000,  closeWith: ['click', 'button'],}).show();
		}	
		if(a.length>1){
			new Noty({ type: 'error', theme: 'mint', layout: 'topRight',  text: 'έχεις επιλέξει περισσότερα από ένα τετράγωνα',  timeout: 1000,  closeWith: ['click', 'button'],}).show();
		}
        for (var e = 0, g = a.length; e < g; e++){ 
		a[e].annotation.group = b.split("__")[0], 
		a[e].annotation.brand = b.split("__")[1], 
		a[e].annotation.tpoint = c, 
		a[e].annotation.hits = parseInt(d, 10), 
		nullAnnoFlag--;
        dehighlightAllObj()
		}
    }else{
		new Noty({ type: 'error', theme: 'mint', layout: 'topRight',  text: 'δεν έχεις επιλέξει touchpoint',  timeout: 1000,  closeWith: ['click', 'button'],}).show();
	}
    $("#hits" ).blur();
    $("#brands ul li").removeClass('selected');
	$("#tpoints ul").remove();
    document.getElementById("hits").selectedIndex = -1
});
	
document.addEventListener("dragstart", function(a) {
    a.preventDefault();
    return !1
});

loadAnn.addEventListener("change", function(a) {
    loadAnnotations();
    loadAnn.blur()
});
loadPresets.addEventListener("change", function(a) {
    loadPresetsFromJson();
    loadPresets.blur()
});	

imgNameInput.addEventListener("change", function(a) {
    if (imgNameInput.value == imName) return a.preventDefault(), !1;
    if ("" != document.getElementById("projectFolder").value) {
        var b = imIndices.indexOf(imgNameInput.value);
        if (-1 == b || imReadFlag) return a.preventDefault(), !1;
        imReadFlag = !0;
        loadImg(b)
    }
    imgNameInput.blur()
});
//////// END Event Listeners

function timestamp() {
	var d = new Date();
	var month = d.getUTCMonth();	//get the month
	var day = d.getDate();		//get the day
	var year = d.getFullYear();		//get the year
	var hours = d.getHours();		//get hours
	var minutes = d.getMinutes();		//get minutes
	var seconds = d.getSeconds();		//get seconds
	year = year.toString().substr(2,2);		//pull the last two digits of the year
	month = month + 1;		//increment month by 1 since it is 0 indexed
	month = month + "";		//converts month to a string
	if (month.length == 1)	{	month = "0" + month;	}		//if month is 1-9 pad right with a 0 for two digits
	day = day + "";		//convert day to string	
	if (day.length == 1)	{	day = "0" + day;	}		//if day is between 1-9 pad right with a 0 for two digits
	hours = hours + "";	//convert hours to string
	if (hours.length == 1)	{	hours = "0" + hours;	}		//if hours is 1-9 pad right with a 0 for two digits
	minutes = minutes + "";	//convert minutes to string
	if (minutes.length == 1)	{	minutes = "0" + minutes;	}		//if minutes is 1-9 pad right with a 0 for two digits
	seconds = seconds + "";	//convert seconds to string
	if (seconds.length == 1)	{	seconds = "0" + seconds;	}		//if seconds is 1-9 pad right with a 0 for two digits
	var mydate = year + month + day;		//return the string "MMddyy"
	//var mytime = hours + minutes + seconds;
	var mytime = hours + minutes;
	
	return mydate + "-" + mytime;
}	

function checkLoadLocalStorage() {
    "undefined" === typeof localStorage && alert("CAUTION: Local storage is not supported by your browser. For this reason autosave will not work. You have to manually save your annotations.");
    if ("undefined" !== typeof localStorage.allAnnotations && "" !== localStorage.allAnnotations) {
        allAnnotations = JSON.parse(localStorage.allAnnotations);
        prefs = allAnnotations.prefs;
        presets = allAnnotations.presets;
        $("#brands").html("");
        resetGUIAnnoInfo();
        document.getElementById("projectName").innerHTML = prefs.projectName
		document.getElementById("AnnotatorName").innerHTML = prefs.AnnotatorName
    }
}

function uniqueArr(list) {
    var result = [];
    $.each(list, function(i, e) {
        if ($.inArray(e, result) == -1) result.push(e);
    });
    return result;
}

function checkConnsChanges(){	//NOT USED
	if ( Object.keys(allAnnotations.images).length>0 ){	//AN YPARXOUN ANNO STI MNHMH
		for ( x in allAnnotations.images ){	// ΓΙΑ ΚΑΘΕ ΕΙΚΟΝΑ ΜΕ ΑΝΝΟ
			var thisannos = allAnnotations.images[x].annotations;
			for ( y in thisannos ) {	// ΓΙΑ ΚΑΘΕ ΑΝΝΟ ΤΗΣ ΕΙΚΟΝΑΣ
				if ( jQuery.inArray( thisannos[y].group, prefs.groups )<0 ){	// ΑΝ ΔΕΝ ΥΠΑΡΧΕΙ ΤΟ ΓΚΡΟΥΠ ΤΟΥ ΑΝΝΟ ΣΤΑ PREFS
					for ( conn in prefs.conns ) {
						if ( prefs.conns[conn].brand == thisannos[y].brand ){ 
							thisannos[y].group = prefs.conns[conn].group ;
						}
					}
				}
				if ( jQuery.inArray( thisannos[y].brand, prefs.brand )<0 ){	// ΑΝ ΔΕΝ ΥΠΑΡΧΕΙ ΤΟ ΓΚΡΟΥΠ ΤΟΥ ΑΝΝΟ ΣΤΑ PREFS
					for ( conn in prefs.conns ) {
						if ( prefs.conns[conn].brand == thisannos[y].brand ){ 
							thisannos[y].group = prefs.conns[conn].group ;
						}
					}
				}
			}
		}
	}
}

function clearProjectPrefsSelection() {
    document.getElementById("projectName").innerHTML = "Load Project";
	document.getElementById("AnnotatorName").innerHTML = "Empty";
    document.getElementById("projectPrefs").value = "";
    document.getElementById("projectPrefsBox").value = "";
	$("#projectPrefsBox").attr('title', "");
    prefs = {
        projectName: "",
		AnnotatorName: "",
        groups: [],
		brands: [],
		tpoints: [],
        prefsFilename: "",
        imgFoldername: "",
		userAdds: {},
		conns: {},
		seelater: []
    };
    resetGUIAnnoInfo();
    $("#brands").html("")
}

function clearProjectFolderSelection() {
    document.getElementById("projectFolder").value = "";
    document.getElementById("projectFolderBox").value = "";
    $("#projectFolderBox").attr( 'title', "");
    if (brd && brd.renderer) try {
        JXG.JSXGraph.freeBoard(brd), document.getElementById("box").setAttribute("style", "width:730px;height:580px;"), imIndices = [], imAll = {}, im = void 0
    } catch (a) {
        console.log("Problem while initializing JSX board. Error: " + a.message)
    }
    $("#imageName").val("");
}

function disableGroups(){
	b = document.getElementById("brands");
	for(i=0;i<b.length;i++){	//disable brand groups selection
		if (b[i].className == "group" )  {
			b[i].disabled=true;
			$(b[i]).addClass("disabled")
		}
	}	
}

function brandsInit() {
	$("#brands ul li ul li").addClass("brand");
	$('#brands ul').sortable({disabled: true});	// MANDATORY FOR SORTABLE TO WORK : adds class "ui-sortable-handle"
	$("#brands ul li ul li").on("click", function(){
			if ( !$(this).hasClass('selected') ){
				$("#brands li").removeClass('selected');
				$(this).addClass('selected');
				
				fillTouchpoints( $("#brands li.selected").attr('id') );
				tpointsInit();
				$("#hits option:selected").prop("selected", false);
			}
	})
}

function tpointsInit() {
	$('#tpoints ul').sortable({disabled: true});	// MANDATORY FOR SORTABLE TO WORK : adds class "ui-sortable-handle"
	if ( $("#tpoints ul li").length>0 && $("#tpoints ul li.selected").length==0 ) $("#tpoints ul li:first").addClass('selected')
	$("#tpoints ul li").on("click", function(){
		if ( !$(this).hasClass('selected') ){
			$("#tpoints li").removeClass('selected')
			$(this).addClass('selected')
		}
	});
}

function fillTouchpoints(conn) {
    var b = $('#tpoints');
    if ( "" !== conn ) {
        $('#tpoints').html("");
		tpoints = prefs.conns[conn].tpoints;
        if (void 0 === tpoints) return console.log("Could not find brand name of annotation, possibly due to altered prefs file."), !1;
        i = 0;
		$('#tpoints').append('<ul></ul>')
        for (var c = tpoints.length; i < c; i++) {
            var d = tpoints[i];
			$('#tpoints ul').append(
				$("<li></li>")
				.attr("id",d)
				// .attr("value",a)
				.text(d)
			); 
        }
        1 == $('#tpoints li').length && ( $('#tpoints').selectedIndex = 0 )
    } else {
		$('#tpoints li').length = 0
	}
	$("#tpoints li").on("click", function(){ document.getElementById("hits").selectedIndex = -1; })
}



function initJSXBoard() {
    if ( 0 === $("#brands ul li").length || "" === prefs.prefsFilename){
		return prefs = {
			projectName: "",
			brands: [],
			seelater: [],
			prefsFilename: "",
			imgFoldername: ""
		};
		alert("You must first load a valid preferences file.");
		clearProjectFolderSelection(), !1;
	}
    if ("" !== document.getElementById("projectFolder").value) {
        if (brd && brd.renderer) try {
            JXG.JSXGraph.freeBoard(brd), 
			document.getElementById("box").setAttribute("style", "width:730px;height:580px;"), 
			imIndices = [], 
			imAll = {}, 
			im = void 0
        } catch (a) {
            console.log("Problem while initializing JSX board. Error: " + a.message)
        }
        imList = document.getElementById("projectFolder").files;
        for (var b = 0, c = imList.length; b < c; b++) {
            var d = imList[b];
            if (d.type.match("image.*")) {
                var e = d.name.split(".")[0];
                imAll[e] = d;
                imIndices.push(e)
            }
        }
        allAnnotations.imageNum = imIndices.length;
        imIndices.sort(alphanumCase);
        imName = imIndices[0];
        prev_imName = imIndices[0];
        prev_imIndex = imIndex = 0;
        "" !== allAnnotations.currentImage && 
		(
		b = imIndices.indexOf(allAnnotations.currentImage), 
		-1 != b && (
			imName = allAnnotations.currentImage, 
			imIndex = b, 
			prev_imName = allAnnotations.currentImage, 
			prev_imIndex = b
			)
		)
    }
    brd = JXG.JSXGraph.initBoard("box", {
        boundingbox: [0, 0, 99, 99],
        keepaspectratio: !0,
        showCopyright: !1,
        showNavigation: !1,
        zoom: !0,
        pan: !0,
        registerEvents: !0
    });
    brd.highlightInfobox = function(a, b, d) {
        if ("point" == d.getType()){
            for (var c in d.childElements) "polygon" == brd.objects[c].getType() && (d = brd.objects[c], group = d.annotation.group, a = d.annotation.brand, b = d.annotation.tpoint, d = d.annotation.hits, "" == a && "" == b ? (a = "NULL", this.infobox.setText('<span style="color:white;font-weight:bold">' + a + "</span>"), 
				this.infobox.rendNode.style.backgroundColor = "red", 
				this.infobox.rendNode.style.padding = "2px") : 
				(
					a = a + " :: " + b + " :: " + d, 
					// a = group + " :: " + a + " :: " + b + " :: " + d, 
					this.infobox.setText('<span style="color:black;font-size:14px;">' + a + "</span>"), 
					this.infobox.rendNode.style.backgroundColor = "#eee", 
					this.infobox.rendNode.style.padding = "2px"
				), 
					this.infobox.rendNode.style.border = "solid white 1px", 
					this.infobox.rendNode.style.borderRadius = "2px"
				)
		}
    };
    if (imReadFlag) return !1;
    imReadFlag = !0;
    loadImg(imIndex);
    brd.on("down", function(a) {
        brd.removeObject(brd.infobox);
        brd.off("up");
        brd.off("move");
        brd.off("over");
        brd.off("update");
        var b = brd.getUsrCoordsOfMouse(a);
        a = brd.getAllUnderMouse(a);
        var d = a[1].elType,
            c, e = brd.create("group", []);
        if ("segment" == d) {
            var v = brd.create("point", b, {
                visible: !1,
                size: 1,
                strokeColor: "#009900",
                fillColor: "#CC0000",
                showinfobox: !1,
                name: "",
                withLabel: !1
            });
            c = a[1].parentPolygon;
            var z = !1,
                p = [];
            if (-1 != highlighted.indexOf(c))
                for (var n = 0, r = highlighted.length; n < r; n++) {
                    var q = highlighted[n],
                        l;
                    for (l in q.ancestors) q.ancestors.hasOwnProperty(l) && p.push(q.ancestors[l])
                } else
                    for (l in c.ancestors) c.ancestors.hasOwnProperty(l) &&
                        p.push(c.ancestors[l]);
            brd.renderer.highlight(c);
            n = c.ancestors[c.getParents()[0]];
            c.getParents();
            var A = 0;
            brd.on("move", function(a) {
                z = !0;
                a = brd.getUsrCoordsOfMouse(a);
                e.addPoints(p);
                e.addPoint(v);
                v.moveTo(a)
            });
            brd.on("up", function(a) {
                brd.off("move");
                brd.suspendUpdate();
                e.ungroup();
                brd.removeObject(v);
				
				!z || 8 > A ? (
						!1 == y && !1 == ctrlPressed && dehighlightAllObj(), 
						highlighted.push(brd, c), 
						brd.removeObject(brd.infobox), 
						brd.initInfobox(), 
						brd.updateInfobox(c.ancestors[Object.keys(c.ancestors)[3]]), 
						a = c.ancestors[Object.keys(c.ancestors)[0]],
						a.setAttribute({ size: 8 })
					) : 
					checkPolyCoords(c) ? removePolygon(c) : ( 
						brd.removeObject(brd.infobox), 
						brd.initInfobox(), 
						brd.updateInfobox( c.ancestors[Object.keys(c.ancestors)[3]] ), 
						a = c.ancestors[Object.keys(c.ancestors)[0]], 
						a.setAttribute({ size: 8 })
					);
                brd.unsuspendUpdate()
            })
        }
        if ("polygon" == d) {
            c = a[1];
            var z = !1,
                v = brd.create("point", b, {
                    visible: !1,
                    size: 1,
                    strokeColor: "yellow",
                    fillColor: "yellow",
                    showinfobox: !1,
                    name: "",
                    withLabel: !1
                }),
                p = [],
                y = !1;
            if (-1 != highlighted.indexOf(c))
                for (y = !0, n = 0, r = highlighted.length; n < r; n++)
                    for (l in q =
                        highlighted[n], q.ancestors) q.ancestors.hasOwnProperty(l) && p.push(q.ancestors[l]);
            else
                for (l in c.ancestors) c.ancestors.hasOwnProperty(l) && p.push(c.ancestors[l]);
            brd.renderer.highlight(c);
            n = c.ancestors[c.getParents()[0]];
            c.getParents();
            n.setAttribute({
                size: 2
            });
            A = 0;
            brd.on("move", function(a) {
                A++;
                z = !0;
                a = brd.getUsrCoordsOfMouse(a);
                e.addPoints(p);
                e.addPoint(v);
                v.moveTo(a)
            });
            brd.on("up", function(a) {
                brd.off("move");
                brd.suspendUpdate();
                e.ungroup();
                brd.removeObject(v);
                !z || 8 > A ? (!1 == y && !1 == ctrlPressed && dehighlightAllObj(),
                    highlighted.push(brd, c), brd.removeObject(brd.infobox), brd.initInfobox(), brd.updateInfobox(c.ancestors[Object.keys(c.ancestors)[3]]), a = c.ancestors[Object.keys(c.ancestors)[0]], a.setAttribute({
                        size: 8
                    })) : checkPolyCoords(c) ? removePolygon(c) : (brd.removeObject(brd.infobox), brd.initInfobox(), brd.updateInfobox(c.ancestors[Object.keys(c.ancestors)[3]]), a = c.ancestors[Object.keys(c.ancestors)[0]], a.setAttribute({
                    size: 8
                }));
                brd.unsuspendUpdate()
            })
        }
        if ("point" == d) brd.on("up", function(a) {
            brd.removeObject(brd.infobox);
            brd.initInfobox()
        });
        if (void 0 === d || "image" === d) {
		   // NEW BOX
            var s = brd.create("point", b, {	//top left circle border  
                    size: 2, 
					strokeColor: "green", 
					fillColor: "red",
                    showinfobox: !1,
                    name: "",
                    withLabel: !1
                }),
                w = brd.create("point", b, {	//bottom right circle border
                    size: 2, 
					strokeColor: "green", 
					fillColor: "none",
                    showinfobox: !1,
                    name: "",
                    withLabel: !1
                }),
                u = brd.create("point", [function() {	//bottom left circle border
                    return s.X()
                }, function() {
                    return w.Y()
                }], {
					size: 2, 
					strokeColor: "green", 
					fillColor: "none",
                    showinfobox: !1,
                    name: "",
                    withLabel: !1
                }),
                x = brd.create("point", [function() {	//top right circle border
                    return w.X()
                }, function() {
                    return s.Y()
                }], {
					size: 2, 
					strokeColor: "green", 
					fillColor: "none",
                    showinfobox: !1,
                    name: "",
                    withLabel: !1
                }),
                t = brd.create("polygon", [s, u, w, x], {	//4 square lines
                    name: "",
                    withLabel: !1,
                    hasInnerPoints: !0,
                    fillColor: "none",
                    highlightFillColor: mouseoverfillcolor,
                    borders: {
                        strokeWidth: 2,
                        fillColor: "white",
						strokeColor: boxborder,
                        highlightStrokeColor: highlightstrokecolor				   
                    }
                });
            t.annotation = {
				group: "",
                brand: "",
                tpoint: "",
                hits: 0
            };
			dehighlightAllObj();
			// NEW BOX END
            for (var B in t.borders) t.borders[B].visProp.highlight = !1;
            brd.on("move", function(a) {
                a = brd.getUsrCoordsOfMouse(a);
                w.moveTo(a)
            });
            brd.on("up", function(a) {
                brd.off("move");
                nullAnnoFlag++;
				hasNull=1;				  
                brd.initInfobox();
                if (checkPolyCoords(t)) removePolygon(t);
                else {
                    var b = [s.X(), w.X(), u.X(), x.X()],
                        c = [s.Y(), w.Y(), u.Y(), x.Y()];
                    a = Math.max.apply(Math, b);
                    var b = Math.min.apply(Math, b),
                        d = Math.max.apply(Math, c),
                        c = Math.min.apply(Math, c);
                    brd.suspendUpdate();
                    s.moveTo([b, c]);
                    w.moveTo([a, d]);
                    u.setAttribute({
                        showinfobox: !0
                    });
                    x.setAttribute({
                        showinfobox: !0
                    });
                    highlighted.push(brd, t);
                    t.on("move", function(a) {
                        s.setAttribute({
                            size: 8
                        });
                        brd.renderer.highlight(this);
                        brd.updateInfobox(x)
                    });
                    t.on("out", function(a) {
                        s.setAttribute({
                            size: 2
                        })
                    });
                    s.on("move", function(a) {
                        this.setAttribute({
                            size: 8
                        })
                    });
                    s.on("out", function(a) {
                        this.setAttribute({
                            size: 2
                        })
                    });
                    s.on("down", function(a) {
                        s.on("up", function(a) {
                            removePolygon(t)
                        })
                    });
                    w.on("down", function(a) {
                        w.on("up", function(a) {
                            checkPolyCoords(t) || (brd.removeObject(brd.infobox), brd.initInfobox(), brd.updateInfobox(t.ancestors[Object.keys(t.ancestors)[3]]), s.setAttribute({
                                size: 8
                            }))
                        })
                    });
                    brd.unsuspendUpdate();
                    brd.updateInfobox(x)
                }
            })
        }
    });
    autosaveTimer = setInterval(function() {
        storeAnnotationImg();
        localStorage.allAnnotations = JSON.stringify(allAnnotations)
		// alert("saved")
    }, autosaveInterval)
}

function gotoImg_noanno(e) {
    if ("" != document.getElementById("projectFolder").value) {
        var b = imIndices.indexOf(e);
        // if (-1 == b || imReadFlag) return a.preventDefault(), !1;
        imReadFlag = !0;
        loadImg(b)
    }
}

function loadImg(a) {
    if (0 < nullAnnoFlag){ 
		highlightNull()
		return new Noty({ type: 'error', theme: 'mint', layout: 'top',  text: 'NULL : κάποιο τετράγωνο δεν έχει πληροφορία',  timeout: 1000,  closeWith: ['click', 'button'],}).show() ,
		imReadFlag = !1;
		
	}
    ( a !== imIndex || 2 < brd.objectsList ) && prepareChangeImg();
    prev_imIndex = imIndex;
    prev_imName = imIndices[imIndex];
    imName = imIndices[a];
 //    if (imName.match(/[a-z]/i)) {
	// 	if (imName.match(/^\d/)) {
	// 		confirm('Wrong image name => ' + imName + '. Please rename images.');
	// 	}
	// }
    imIndex = a;
    if (0 != imIndices.length) {
        a = new FileReader;
        a.onloadend = function(a) {
            var b = new Image;
            b.onload = function() {
                if ( b.width == imWidth && b.height == imHeight && void 0 !== im ){
					im.url = a.target.result;
				}else{
					imWidth = b.width;
					imHeight = b.height;
					730 < imWidth && (imAspectRatio =imWidth / imHeight, imWidth = Math.abs(730), imHeight = 1 / imAspectRatio * imWidth);
					void 0 !== im && brd.removeObject(im);
					im = brd.create(
						"image", 
						[a.target.result, [1, imHeight],[imWidth, imHeight]], 
						{
							layer: 0,
							highlightFillColor: mouseoverfillcolor,
							hightlighted: "off"
						}
					);
					im.visProp.highlight = !1;
					im.isDraggable = !1;
					document.getElementById("box").setAttribute("style", "width:" + imWidth + "px;height:" + imHeight + "px;");
					brd.resizeContainer(imWidth, imHeight);
					brd.setBoundingBox([1, 1, imWidth, imHeight], !1)
				}
                brd.update();
                afterChangeImg();
				//	prostheto gia ta lock presets
				if ( lockedpreset !== "" ){
					if( imIndex<prev_imIndex ){
						lockedpreset = "";
						new Noty({ type: 'error', theme: 'mint', layout: 'topRight',  text: 'lock preset disabled',  timeout: 1000,  closeWith: ['click', 'button'],}).show();
					}else{
						pasteLastPreset( lockedpreset ) 
					}
				}
				///////
                imReadFlag = !1;
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

function prepareChangeImg() {
// if ( 2 < brd.objectsList.length ){ checkDoubleByPos() }
if ( 2 < brd.objectsList.length ){ checkDoubleByAnno() }
    brd.off("up");
    brd.off("move");
    brd.off("update");
	storeAnnotationImg();
	// storeEXIFdataImg();
	highlightAllObj();
    0 != highlighted.length && storeD("end");
    removeAllObj()	
}

function afterChangeImg() {
    allAnnotations.currentImage = imName;
	resetGUIAnnoInfo();
	loadAnnotationImg()
	if ( prevopen==true ) {	preview(); }
}

function loadAnnFiles() {}

function removeBoxDups(e) {
	 // e format : "01457"
}

function loadAnnotations() {
    var a = document.getElementById("loadAnn").files[0],
        b = new FileReader;
    b.onload = function(a) {
        a = JSON.parse(a.target.result);
        if (document.getElementById("mergeAnn").checked) {
			
            allAnnotations.project = a.project;
            allAnnotations.imageNum = a.imageNum;
            allAnnotations.prefs = a.prefs;
            // prefs = allAnnotations.prefs;	//BUG FIX
			if ( prefs.seelater.length>0 ) { 
				$("#laterdiv").show() 
				$('button#laterlist').click()
			}
	
            allAnnotations.currentImage = a.currentImage;
            for (var b in a.images) 0 != a.images[b].annotations.length && (allAnnotations.images[b] = a.images[b]);
            for (var e in allAnnotations.presets) 0 == allAnnotations.presets[e].length &&
                (allAnnotations.presets[e] = a.presets[e])
        } else {
			allAnnotations = a;
		}
        brd && brd.renderer && (removeAllObj(), loadAnnotationImg())
    };
    b.onloadstart = function(a) {
		
    };
    b.onloadend = function(a) {
		
		// actions to remove duplicate boxes from last json frame
		var c = imIndices.indexOf(allAnnotations.currentImage);
        if (-1 == c || imReadFlag) return a.preventDefault(), !1;
        imReadFlag = !0;
        loadImg(c)
    };
    b.onerror = function(a) {
        console.error("Could not load the selected annotations file! Code " + a.target.error.code)
    };
    b.readAsText(a)
	// GO TO LAST ANNO IMAGE
	// var lastImName = Object.keys ( allAnnotations.images )[ Object.keys ( allAnnotations.images ).length-1 ]
	// if ( imIndices.indexOf( lastImName )>-1 ){
		// loadImg( imIndices.indexOf( lastImName ) )
	// }else{
		// loadImg( imIndices.length-1 )
	// }
}

function loadOptions() {	//NOT USED
	var a = document.getElementById("loadOpts").files[0],
	b = new FileReader;
	b.onload = function(a) {
		a = JSON.parse(a.target.result);
		// console.log(a.prefs.groups)
	
		$("#brands").html("<ul></ul>");
		//bazei ta ul li
		for (i in a.prefs.groups) {
			$("#brands ul").append(
				$("<li></li>")
				.attr("id",a.prefs.groups[i])
				.attr("class","group")
				.attr("value",a.prefs.groups[i])
				.html(a.prefs.groups[i])
			);
		}
		$("#brands ul li").append('<ul></ul>');
		for (key in a.prefs.conns) {
			if ( a.prefs.conns.hasOwnProperty(key) ){
				br = a.prefs.conns[key].brand;
				$("#brands ul li").each(function(){
					if( $(this).attr('id')==a.prefs.conns[key].group ){
						$('ul', this).append( $("<li></li>").attr("id",key).attr("value",br).text(br) ); 
					}
				})
			}
		}
		disableGroups();
		resetGUIAnnoInfo();
		allAnnotations.project = prefs.projectName;
		allAnnotations.Annotator = prefs.AnnotatorName; //tassos
		allAnnotations.prefs = prefs;
		brandsInit();
	
		allAnnotations.prefs = a.prefs;
		for (var e in allAnnotations.presets) 0 == allAnnotations.presets[e].length &&	(allAnnotations.presets[e] = a.presets[e])
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

function storeAnnotationImg() {
    if (void 0 === imName) return !1;
    var a = {};
    a.imageName = imName;
    a.imageIndex = imIndex;
    a.width = imWidth;
    a.height = imHeight;
    a.annotations = [];
	
	for (var b = 0; b < brd.objectsList.length; b++){
		var obj = brd.objectsList[b];
		if ( obj.getType() == "polygon" && obj.getAttribute("visible") == !0) {
			var d = {};
			d.startPoint = getPolyStartDiag(obj).start;
			d.diagPoint = getPolyStartDiag(obj).diag;
			d.group = obj.annotation.group;
			d.brand = obj.annotation.brand;
			d.tpoint = obj.annotation.tpoint;
			d.hits = obj.annotation.hits;
			a.annotations.push(d);
		}
	}
	if( a.annotations.length ){
		allAnnotations.images[imName] = a
		var x = imName;
		allAnnotations.images[x].exifdata || EXIF.getData(imAll[x], function() {
			allAnnotations.images[x].exifdata = this.exifdata;
		})
	}else{
		delete allAnnotations.images[imName]	//if there was only one box and was deleted
	}
}

function storeEXIFdataImg() {
    // if (void 0 === imName) return !1;
    // var a = imName;
    // allAnnotations.images[a].exifdata || EXIF.getData(imAll[a], function() {
        // allAnnotations.images[a].exifdata = this.exifdata;
        // return imAll[a].exifdata
    // })
}

function loadAnnotationImg() {
    if (allAnnotations.images.hasOwnProperty(imName)) {
        var a = allAnnotations.images[imName].annotations;
        brd.suspendUpdate();
        for (var b = 0, c = a.length; b < c; b++) createPolygon(a[b].startPoint, a[b].diagPoint).annotation = {
            group: a[b].group,
            brand: a[b].brand,
            tpoint: a[b].tpoint,
            hits: a[b].hits
        };
        brd.unsuspendUpdate()
    }
}

function loadNextImg() {
    var a = imIndex;
    if (brd && brd.renderer && a < imIndices.length - 1) {
        a++;
        if (imReadFlag) return !1;
        imReadFlag = !0;
        loadImg(a)
    }
	if (nullAnnoFlag<0) alert ('nullAnnoFlag < 0')	
}

function checkDoubleByPos(){
	var a = brd.objects, b, pos=[];
	for ( b in a ){
		if ( a[b].getType()=="polygon" ){
			if ( $.inArray( $('#box_'+a[b].id).position().top+"_"+$('#box_'+a[b].id).position().left, pos ) >-1 ){
				new Noty({ type: 'error', theme: 'mint', layout: 'top',  
					text: 'διπλότυπο στην προηγούμενη εικόνα : '+a[b].annotation.brand+" - "+a[b].annotation.tpoint,  timeout: 3000,  closeWith: ['click', 'button'],}).show();
					break
			}else{
				pos.push( $('#box_'+a[b].id).position().top+"_"+$('#box_'+a[b].id).position().left )
			}
		}
	}
}

function checkDoubleByAnno(){
	var a = brd.objects, b, pos=[];
	for ( b in a ){
		if ( a[b].getType()=="polygon" ){
			if ( $.inArray( a[b].annotation.brand+"__"+a[b].annotation.tpoint, pos ) >-1 ){
				new Noty({ type: 'error', theme: 'mint', layout: 'top',  
					text: 'διπλότυπο στην προηγούμενη εικόνα : '+a[b].annotation.brand+" - "+a[b].annotation.tpoint,  timeout: 3000,  closeWith: ['click', 'button'],}).show();
					break
			}else{
				pos.push( a[b].annotation.brand+"__"+a[b].annotation.tpoint )
			}
		}
	}
}

function loadNext10Img() {
    var a = imIndex;
    if (brd && brd.renderer) {
        a = a < imIndices.length - 1 - 10 ? a + 10 : imIndices.length - 1;
        if (imReadFlag || a == imIndex) return !1;
        imReadFlag = !0;
        loadImg(a)
    }
}

function loadPrevImg() {
    // document.getElementById("prevButton").blur();
    var a = imIndex;
    if (brd && brd.renderer && 1 <= a) {
        a--;
        if (imReadFlag) return !1;
        imReadFlag = !0;
        loadImg(a)
    }
}

function loadPrev10Img() {
    var a = imIndex;
    if (brd && brd.renderer) {
        a = 10 <= a ? a - 10 : 0;
        if (imReadFlag || a == imIndex) return !1;
        imReadFlag = !0;
        loadImg(a)
    }
}

function goNextImg() {
    loadNextImg()
}

function goBackImg() {
    document.getElementById("backButton").blur();
    if (imReadFlag) return !1;
    imReadFlag = !0;
    brd && brd.renderer && loadImg(prev_imIndex)
}

function removeHighlightedObj() {
    brd.suspendUpdate();
    brd.removeObject(brd.infobox);
    brd.initInfobox();
    for (var a = highlighted, b = 0, c = a.length; b < c; b++) {
        if (a[b].ancestors)
            for (var d in a[b].ancestors) brd.removeObject(a[b].ancestors[d]);
        void 0 === a[b].annotation || "" !== a[b].annotation.brand && "" !== a[b].annotation.tpoint || nullAnnoFlag--;
		// if(nullAnnoFlag<0){nullAnnoFlag=0}					  
        brd.removeObject(a[b])
    }
    highlighted.length = 0;
    brd.unsuspendUpdate();
    resetGUIAnnoInfo()
}

function removeAllObj() {
    brd.suspendUpdate();
    brd.removeObject(brd.infobox);
    brd.initInfobox();
    var a = brd.objects,
        b;
    for (b in a)
        if (a[b] && "polygon" == a[b].elType && !1 != a[b].getAttribute("visible")) {
            var c = a[b].getParents();
            brd.removeObject(a[b]);
            for (var d in c) brd.removeObject(c[d])
        }
    brd.unsuspendUpdate();
    removeHighlightedObj();
    nullAnnoFlag = 0;
    resetGUIAnnoInfo()
}

function removePresetObj(a) {
    allAnnotations.presets[a] = []
}

highlighted.push = function(a, b) {
    switch (b.elType) {
        case "polygon":
            if (-1 == this.indexOf(b)) {
                b.setAttribute({
                    fillColor: "none"
                });
                for (var c = 0, d = b.borders.length; c < d; c++) b.borders[c].setAttribute({
                    strokewidth: highlightstrokecolorwidth,
					strokecolor: highlightstrokecolor
                });
                0 == highlighted.length ? updateGUIAnnoInfo(b) : resetGUIAnnoInfo();
                return Array.prototype.push.apply(this, [b])
            }
            b.setAttribute({
                fillColor: "none"
            });
            c = 0;
            for (d = b.borders.length; c < d; c++) b.borders[c].setAttribute({
                strokewidth: boxborderwidth,
                strokecolor: boxborder	//inactive box borders
            });
            2 == highlighted.length && (c = highlighted.slice(0),  c.splice(this.indexOf(b), 1), updateGUIAnnoInfo(c[0]));
            1 == highlighted.length && resetGUIAnnoInfo();
            return Array.prototype.splice.apply(this, [this.indexOf(b), 1])
    }
};

function updateGUIAnnoInfo(a) {
    var gr = a.annotation.group,
		br = a.annotation.brand,
        tp = a.annotation.tpoint,
		hits = a.annotation.hits;
    if ("" == br ){ 
		$("#brands ul li").removeClass('selected');
		$("#tpoints ul li").removeClass('selected');
	}else{ 
		$("#brands ul li").removeClass('selected');
		$("#tpoints ul li").removeClass('selected');
		
		if ( prefs.conns.hasOwnProperty( gr+"__"+br ) ) { // GIA TIN PERIPTOSI POU EXEI ALLAKSEI TO ONOMA BRAND-GROUP I EXEI AFAIRETHEI KATI AP TA DUO
			$("#brands ul li[id='"+gr+"__"+br+"']").addClass('selected')
			brandScrollTo();
			fillTouchpoints( gr+"__"+br ); 
			$("#tpoints ul li[id='"+tp+"']").addClass('selected')
			
			if ( "" == hits ){ 
				document.getElementById("hits").selectedIndex = -1;
			}else {
				document.getElementById("hits").value = hits
			}
			tpointsInit();
		}
	}
}

function resetGUIAnnoInfo() {
    $("#brands ul li").removeClass('selected');
    $("#tpoints ul li").removeClass('selected');
    document.getElementById("hits").selectedIndex = -1
	$("#tpoints ul").remove();
}

function highlightAllObj() {
    brd.suspendUpdate();
    var a = brd.objects,
        b;
    for (b in a) a[b] && "polygon" == a[b].getType() && !1 != a[b].getAttribute("visible") && -1 == highlighted.indexOf(a[b]) && highlighted.push(brd, a[b]);
    brd.unsuspendUpdate()
}

function highlightNull() {
    brd.suspendUpdate();
    var a = brd.objects,
        b;
    for (b in a) a[b] && "polygon" == a[b].getType() && ""== a[b].annotation.brand && !1 != a[b].getAttribute("visible") && -1 == highlighted.indexOf(a[b]) && highlighted.push(brd, a[b]);
    brd.unsuspendUpdate()
}

function dehighlightAllObj() {
    brd.suspendUpdate();
    var a = brd.objects,
        b;
    for (b in a) a[b] && "polygon" == a[b].getType() && !1 != a[b].getAttribute("visible") && -1 != highlighted.indexOf(a[b]) && highlighted.push(brd, a[b]);
    brd.unsuspendUpdate()
	$("#brands").scrollTop(0)
}

function removePolygon(a) {
    void 0 === a.annotation || "" !== a.annotation.brand && "" !== a.annotation.tpoint || nullAnnoFlag--;
	// if(nullAnnoFlag<0){nullAnnoFlag=0}						   
    brd.removeObject(brd.infobox);
    brd.initInfobox(); - 1 < highlighted.indexOf(a) && highlighted.push(brd, a);
    for (var b in a.ancestors) brd.removeObject(a.ancestors[b]);
    brd.removeObject(a)
}

function checkPolyCoords(a) {
    var b = a.ancestors[Object.keys(a.ancestors)[0]].X();
    1 > b ? b = 1 : b > imWidth && (b = imWidth);
    var c = a.ancestors[Object.keys(a.ancestors)[0]].Y();
    1 > c ? c = 1 : c > imHeight && (c = imHeight);
    var d = a.ancestors[Object.keys(a.ancestors)[2]].X();
    1 > d ? d = 1 : d > imWidth && (d = imWidth);
    var e = a.ancestors[Object.keys(a.ancestors)[2]].Y();
    1 > e ? e = 1 : e > imHeight && (e = imHeight);
    brd.suspendUpdate();
    a.ancestors[Object.keys(a.ancestors)[0]].moveTo([b, c]);
    a.ancestors[Object.keys(a.ancestors)[2]].moveTo([d, e]);
    if (10 > a.borders[0].L() ||
        10 > a.borders[1].L()) return brd.unsuspendUpdate(), !0;
    brd.unsuspendUpdate();
    return !1
}

function getPolyStartDiag(a) {
    var b = a.getParents()[0],
        c = brd.objects[b].X(),
        b = brd.objects[b].Y(),
        d = a.getParents()[2];
    a = brd.objects[d].X();
    d = brd.objects[d].Y();
    return {
        start: [c, b],
        diag: [a, d]
    }
}

function createPolygon(a, b) {		// pasted preset
    var c = brd.create("point", a, {
            size: 2,
            strokeColor: dotstrokecolor,
            fillColor: "none",
            showinfobox: !1,
            name: "",
            withLabel: !1
        }),
		d = brd.create("point", b, {
            size: 2,
            strokeColor: dotstrokecolor,
            fillColor: "none",
            showinfobox: !1,
            name: "",
            withLabel: !1
        }),
		e = brd.create("point", [ function(){ 
            return c.X()
        }, function() {
            return d.Y()
        }], {
            size: 2,
            strokeColor: dotstrokecolor,
            fillColor: "#CC0000",
            name: "",
            withLabel: !1
        }),
        g = brd.create("point", [function() {
            return d.X()
        }, function() {
            return c.Y()
        }], {
            size: 2,
            strokeColor: dotstrokecolor,
            fillColor: "#CC0000",
            name: "",
            withLabel: !1
        }),
		f = brd.create("polygon", [c, e, d, g], {
            name: "",
            withLabel: !1,
            hasInnerPoints: !0,
            fillColor: "none",
            highlightFillColor: mouseoverfillcolor,
            borders: {
                strokeWidth: boxborderwidth,
                strokeColor: boxborder,
                highlightStrokeColor: highlightstrokecolor
            }
        });
    f.annotation = {
        group: "",
        brand: "",
        tpoint: "",
        hits: 0
    };
    f.on("move", function(a) {
        c.setAttribute({
            size: 8
        });
        brd.renderer.highlight(this);
        brd.updateInfobox(g)
    });
    f.on("out", function(a) {
        c.setAttribute({
            size: 2
        })
    });
    c.on("move", function(a) {        
		this.setAttribute({
            size: 8
        })
    });
    c.on("out", function(a) {
        this.setAttribute({
            size: 2
        })
    });
    c.on("down", function(a) {
        c.on("up", function(a) {
            removePolygon(f)
        })
    });
    d.on("down", function(a) {
        d.on("up", function(a) {
            checkPolyCoords(f) ? removePolygon(polygon) : (brd.removeObject(brd.infobox), brd.initInfobox(), brd.updateInfobox(f.ancestors[Object.keys(f.ancestors)[3]]), c.setAttribute({
                size: 8
            }))
        })
    });
    for (var h in f.borders) f.borders[h].visProp.highlight = !1;
    return f
}

function clonePolyInvisible(a) {
    var b = getPolyStartDiag(a);
    a = a.annotation;
    b = createPolygon(b.start, b.diag);
    b.setAttribute({
        visible: !1
    });
    for (var c in b.ancestors) b.ancestors.hasOwnProperty(c) && b.ancestors[c].setAttribute({
        visible: !1
    });
    b.annotation = {};
    b.annotation.conn = a.conn;
    b.annotation.brand = a.brand;
    b.annotation.tpoint = a.tpoint;
    b.annotation.hits = a.hits;
    return b
}

function createPreset(x) {
	var a = [];
    for ( b = 0 ; b < highlighted.length; b++) {
		var d = getPolyStartDiag(highlighted[b]),
		e = highlighted[b].annotation;
        d.annotation = {};
		if ( e.brand!=="" && e.tpoint!=="" ) { 
			d.annotation.group = e.group;
			d.annotation.brand = e.brand;
			d.annotation.tpoint = e.tpoint;
			d.annotation.hits = e.hits;
			a.push(d)
			new Noty({ type: 'success', theme: 'mint', layout: 'bottomRight',  text: 'η μνήμη αποθηκεύτηκε στο <b>: '+x+'</b>',  progressBar: false, timeout: 1000 }).show()
		}
		else{
			new Noty({ type: 'error', theme: 'mint', layout: 'topRight',  text: 'έχεις αποθηκεύσει κενό annotation',  timeout: 3000,  closeWith: ['click', 'button'],}).show();
		}

    }
	return a
}

function storePreset(a) {
	if ( highlighted.length>0 ){
		removePresetObj(a);
		var b = createPreset(a);
		allAnnotations.presets[a] = b
	}
	else {
		new Noty({ type: 'error',  layout: 'topRight',  text: 'κανένα επιλεγμένο τετράγωνο',  timeout: 3000,  closeWith: ['click', 'button'],}).show();
	}
}

function storeD(a) {
    removePresetObj(a);
	
	for (var x = [], b = 0, c = highlighted.length; b < c; b++) {
		var d = getPolyStartDiag(highlighted[b]),
		e = highlighted[b].annotation;
        d.annotation = {};
			d.annotation.group = e.group;
			d.annotation.brand = e.brand;
			d.annotation.tpoint = e.tpoint;
			d.annotation.hits = e.hits;
			x.push(d)
    }
	
    allAnnotations.presets[a] = x
}

function pastePreset(a) {
	dehighlightAllObj();
    a = allAnnotations.presets[a];
    brd.suspendUpdate();	
	
    for (var b = 0, c = a.length; b < c; b++) {
        var d = a[b].annotation,
        e = createPolygon(a[b].start, a[b].diag);
        e.annotation = {};
        e.annotation.group = d.group;
        e.annotation.brand = d.brand;
        e.annotation.tpoint = d.tpoint;
        e.annotation.hits = d.hits;

		highlighted.push(brd, e)
    }
    brd.unsuspendUpdate()
}

function pasteLastPreset(a) {
	dehighlightAllObj();
    a = allAnnotations.presets[a];
    brd.suspendUpdate();	
	
    for (var b = 0, c = a.length; b < c; b++) {
        var d = a[b].annotation,
        e = createPolygon(a[b].start, a[b].diag);
        e.annotation = {};
		e.annotation.group = d.group;
        e.annotation.brand = d.brand;
        e.annotation.tpoint = d.tpoint;
        e.annotation.hits = d.hits;
    }
    brd.unsuspendUpdate()
}

function makePolyVisible(a) {
    var b = {},
        b = "object" === typeof a ? a : brd.objects[a];
    a = b.getParents();
    for (var c = 0, d = a.length - 1; c < d; c++) brd.objects[a[c]].setAttribute({
        visible: !0
    });
    b.setAttribute({
        visible: !0
    })
}

function makePolyInvisible(a) {
    var b = {},
        b = "object" === typeof a ? a : brd.objects[a];
    a = b.getParents();
    for (var c = 0, d = a.length - 1; c < d; c++) brd.objects[a[c]].setAttribute({
        visible: !1
    });
    b.setAttribute({
        visible: !1
    })
}

function checkImagePart(a, b, c, d) {
    return c < a / 4 ? d < b / 2 ? "B" : "E" : c >= a / 4 && c < a / 2 ? d < b / 4 ? "B" : d >= 3 * b / 4 ? "E" : "A" : c >= a / 2 && c < 3 * a / 4 ? d < b / 4 ? "C" : d >= 3 * b / 4 ? "D" : "A" : d < b / 2 ? "C" : "D"
}

function hour24ToSecs(a) {
    var b = "",
        b = "number" == typeof a ? a.toString() : a,
        b = b.replace(/:/g, "");
    a = 0;
    if (4 <= b.length) {
        a = parseInt(b.substr(0, 2), 10);
        var c = parseInt(b.substr(2, 2), 10),
            d = 0;
        6 <= b.length && (d = 6 == b.length ? parseInt(b.substr(4, 2), 10) : 0);
        a = 3600 * a + 60 * c + d
    }
    return a
}

function secsToHour24(a) {
    var b = 0,
        b = "string" == typeof a ? parseInt(a, 10) : a;
    a = Math.floor(b / 3600);
    var c = Math.floor((b - 3600 * a) / 60),
        b = b - 3600 * a - 60 * c;
    10 > a && (a = "0" + a);
    10 > c && (c = "0" + c);
    10 > b && (b = "0" + b);
    return a + ":" + c + ":" + b
}

function isKeyPressed(event) {
    if (event.shiftKey) {
        return 1;
    } else {
        return 0;
    }
}

$('#toptoggle i').click(function(){
	$('#toppanel').slideToggle( 'fast' , 'swing' )
	$('#toptoggle i').toggleClass('fa-arrow-circle-o-down')
	$('#toptoggle i').toggleClass('fa-arrow-circle-o-up')
	
})
var switchToInput = function () {
	var thisId = $(this).attr('id')
    var $input = $("<input>", {
        val: $(this).text(),
        type: "text"
    });
    $input.addClass("editable").attr('id', thisId);
    $(this).replaceWith($input);
	$input.on('keyup', function (e) {
		if (e.keyCode == 13) {
			$input.blur()
		}
	});
    $input.on("blur", switchToSpan);
    $input.select();
};
var switchToSpan = function () {
	var thisId = $(this).attr('id')
    var $span = $("<span>", {
        text: $(this).val()
    });
    $span.addClass("editable").attr('id', thisId);
    $(this).replaceWith($span);
    $span.on("click", switchToInput);
	if ( thisId == "projectName" ){ 
		prefs.projectName = $('span#projectName').text()
		allAnnotations.project = prefs.projectName;
		
	}
	if ( thisId == "AnnotatorName" ){ 
		prefs.AnnotatorName = $('span#AnnotatorName').text()
		allAnnotations.Annotator = prefs.AnnotatorName;
	}
};
$("span.editable").on("click", switchToInput);


