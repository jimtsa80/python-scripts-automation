
function downloadAnnotations() {
    if (0 < nullAnnoFlag){ 
		return new Noty({ type: 'error', theme: 'mint', layout: 'topRight',  text: 'έχεις NULL',  timeout: 1000,  closeWith: ['click', 'button'],}).show();
		imReadFlag = !1;
	}
	if( ""==$("#AnnotatorName").html() ){alert("please enter annotator name !");return!1};	
    $("#downloadAnn").blur();
    // if ("" == $("#projectFolder").val()) return !1;
    storeAnnotationImg();
	
	allAnnotations.prefs = prefs
	
    var a = JSON.stringify(allAnnotations);
    localStorage.allAnnotations = a;
    a = new Blob([a], {
        type: "application/json"
    });
    saveAs(a, allAnnotations.project.replace(/ /g,'_').replace(/---|--/g,'-') + "-" + allAnnotations.Annotator + "-" + timestamp() + ".json");
}

function commonExportData(){
	var projArr=allAnnotations.project.split("_"),
	projStart = projArr[projArr.length-1] || "0000",	//an den to brei bazei 0000
	c = isNaN(hour24ToSecs(projStart))?0:hour24ToSecs(projStart),
	annoimgs = Object.keys(allAnnotations.images);
	annoimgs.sort(alphanumCase);

	var annorows=[], prev_annoimgObj= {};
	for (img in allAnnotations.images) {
		var 
		eachdata = allAnnotations.images[img],//px: {imageName: "00012", imageIndex: 11, width: 730, height: 410.625, annotations: Array(1), …}
		X = eachdata.width,
		Y = eachdata.height,
		imgarea = X*Y,
		imgannos = eachdata.annotations,
		n = 1<imgannos.length?0:1, //solus
		offset = parseInt(img) || eachdata.imageIndex,
		timeformat = secsToHour24(c + offset),
		imgannosObj = {};

		for (x=0; x<imgannos.length; x++) {//gia kathe anno tis eikonas
			// if( offset == parseInt(imIndices[imIndices.length-1]) )break;  //tassos : an einai to teleutaio frame
			var gr = imgannos[x].group,
			br = imgannos[x].brand,	//px: {startPoint: (see below), diagPoint: (see below), group: "CONCACAF", brand: "Allstate", tpoint: "LED Sign - Solo Sprint", …}
			tp = imgannos[x].tpoint,
			hts = imgannos[x].hits,
			start = imgannos[x].startPoint, //eg: [29.959722222222226, 34.94097222222223]	( topleft corner position )
			end = imgannos[x].diagPoint,	//eg: [41.94305555555551, 275.5225694444447] 	( bottomright corner position )
			loc = checkImagePart(X, Y, start[0] + Math.round((end[0]-start[0]) / 2 ), start[1] + Math.round((end[1]-start[1])/2)),
			boxW = Math.abs(end[0]-start[0]),	//box width
			boxH = Math.abs(end[1]-start[1]),	//box height
			sizeperc = Math.round(boxW*boxH / imgarea*1E5) / 1E3;
			// annorows[offset+"::"+br+"::"+tp+"::"+loc] = {		//AN XREIASTOUME KAI LOCATION DIAXORISMO
			annorows[offset+"::"+gr+"::"+br+"::"+tp] = {
				group : gr,
				brand : br,
				tpoint : tp,
				time : timeformat,
				duration : 1,
				solus : n,
				location: loc,
				size : sizeperc,
				hits : hts,
				avgHits : hts/1,
				frameNum : img,
				annoTimeOffset : offset
			}
		}
	}
	return annorows;
}

function generateVideoCSV(){
	if( ""==$("#AnnotatorName").html() ){alert("please enter annotator name !");return!1};
	var a=[];
	$("#generateVideoCSV").blur();
	if(""==$("#projectFolder").val())return!1;
	storeAnnotationImg();
	var output="Brand\tLocation\tTime the brand is at screen\tDuration\tScreen Location\tScreen Size %\tTotal Hits\tAverage Hits\tSequence Frame Number\n";
	
	var annorows = commonExportData();
	
	annokeys=Object.keys(annorows);	
	annokeys.sort(alphanumCase);
	var prev="", current="";
	for ( var i=0; i<annokeys.length; i++ ) {
		if ( prev.length>0 ) {	//AN DEN EINAI TO PROTO
			current = annokeys[i]; 		// px: "34::Group:Allstate::Bib"
			if ( parseInt( current.split("::")[0] ) == parseInt( prev.split("::")[0] )+1 ) {	// AN EINAI SUNEXOMENO OFFSET AP TO PROIGOUMENO
				for ( j=0; j<annokeys.length-i; j++ ){	// GIA OLA TA EPOMENA
					if ( annokeys[i+j].split("::")[0] > annokeys[i].split("::")[0] ) {	//AN TO EPOMENO EXEI ALLO OFFSET TOTE BREAK
						break;
					}
						//AN TO PROIGOUMENO EXEI IDIO GROUP,BRAND,TPOINT
					if ( annorows.hasOwnProperty( prev.split("::")[0] +"::"+ annokeys[i+j].split("::")[1] +"::"+ annokeys[i+j].split("::")[2] +"::"+ annokeys[i+j].split("::")[3] ) ){
						// console.log(annokeys[i+j])
						prev = prev.split("::")[0] +"::"+ annokeys[i+j].split("::")[1] +"::"+ annokeys[i+j].split("::")[2] +"::"+ annokeys[i+j].split("::")[3]
						current = annokeys[i+j].split("::")[0] +"::"+ annokeys[i+j].split("::")[1] +"::"+ annokeys[i+j].split("::")[2] +"::"+ annokeys[i+j].split("::")[3]
						
						annorows[ current ].frameNum = annorows[ prev ].frameNum;
						annorows[ current ].time = annorows[ prev ].time;
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
		output += finalrows [ finalkeys[d] ].brand + "\t" 
			+finalrows [ finalkeys[d] ].tpoint + "\t"
			+finalrows[ finalkeys[d] ].time + "\t"
			+finalrows[ finalkeys[d] ].duration + "\t"
			+finalrows[ finalkeys[d] ].location + "\t"
			+finalrows[ finalkeys[d] ].size.toFixed(3) + "\t"
			+finalrows[ finalkeys[d] ].hits + "\t"
			+finalrows[ finalkeys[d] ].avgHits + "\t"
			+(parseInt(finalrows[ finalkeys[d] ].frameNum)||finalrows[ finalkeys[d] ].frameNum) + "\n";
	}
	window.URL = window.webkitURL || window.URL;
	var contentType = 'text/csv';
	var csvFile = new Blob([output], {type: contentType});
	saveAs(csvFile, allAnnotations.project.replace(/ /g,'_').replace(/---|--/g,'-') + "-" + allAnnotations.Annotator + "-" + timestamp() + "-Video.csv"); 
}

function generatePhotoCSV() {
	if(""==$("#AnnotatorName").html()){alert("please enter annotator name !");return!1};
    function a(d) {
        document.getElementById('modal-body').innerHTML = "<h3>" + d + " ||| " + (imIndices.length - 1) + "</h3>";
        // console.log(d + " ||| " + (imIndices.length - 1));
        var e = imIndices[d];
        if (allAnnotations.images.hasOwnProperty(e) && 0 < allAnnotations.images[e].annotations.length) {
            var g = function() {
                    if (k.DocumentName && k.ImageUniqueID)
                        for (var a = k.DocumentName, b = k.ImageUniqueID.split(","), d = 0, g = h.length; d < g; d++)
                            for (var n = h[d].brand, r = h[d].tpoint, q = h[d].hits, l = h[d].startPoint, A = h[d].diagPoint, y = Math.abs(A[0] - l[0]), l = Math.abs(A[1] - l[1]), y = Math.round(y * l / f * 1E5) / 1E3, n = {
                                    image: e,
                                    url: a,
                                    brand: n,
                                    tpoint: r,
                                    hits: q,
                                    percent: y
                                }, r = 0, q = b.length; r <
                                q; r++) c[b[r]] || (c[b[r]] = []), c[b[r]].push(n)
                },
                f = allAnnotations.images[e].width * allAnnotations.images[e].height,
                h = allAnnotations.images[e].annotations,
                k = {};
            allAnnotations.images[e].exifdata ? (k = allAnnotations.images[e].exifdata, g(), d < imIndices.length - 1 ? a(d + 1) : b()) : EXIF.getData(imAll[e], function() {
                k = allAnnotations.images[e].exifdata = this.exifdata;
                g();
                try {
                    d < imIndices.length - 1 ? a(d + 1) : b()
                } catch(e) {
                    console.log("Error", e);
                    //b();
                }
            })
        } else {
            //try {
                if (d < imIndices.length - 1) {
                    setTimeout(function() { a(d + 1); }, 1);
                    //console.log(d+1);
                    //a(d + 1);
                } else { 
                    b();
                }
            //} catch(e) {
                //console.log("Error", e);
                //b();
            //}
        }
    }

    function b() {
        var a = "ArtID\tPhotoID\tPhotoURL\tSponsor\tTouchpoint\tPercentage\tOther\n",
            b;
        for (b in c)
            for (var g = c[b], f = 0, h = g.length; f < h; f++) var k = g[f],
                a = a + (b + "\t" + k.image + "\t" + k.url + "\t" + k.brand + "\t" + k.tpoint + "\t" + k.percent + "\t" + k.hits + "\n");
		
		window.URL = window.webkitURL || window.URL;
		var contentType = 'text/csv';
		var csvFile = new Blob([a], {type: contentType});
		saveAs( csvFile, allAnnotations.project.replace(/ /g,'_').replace(/---|--/g,'-') + "-" + allAnnotations.Annotator + "-" + timestamp() + "-WebPhotos.csv" ); //v24.8
		hideSpinner()
    }
    $("#generatePhotoCSV").blur();
    if ("" == $("#projectFolder").val()) return !1;
	showSpinner();
    storeAnnotationImg();
    var c = {};
    a(0)
}

function generateNewsCSV() { //old news format
	if(""==$("#AnnotatorName").html()){alert("please enter annotator name !");return!1};
    var a = [];
    $("#generateNewsCSV").blur();
    if ("" == $("#projectFolder").val()) return !1;
    storeAnnotationImg();
    var b = $("#workspace"),
        b = b.options[b.selectedIndex].text.toLowerCase(),
        d = allAnnotations.project.split("_"),
        c = d[d.length - 1] || "0000",
        f = isNaN(hour24ToSecs(c)) ? 0 : hour24ToSecs(c),
        c = "Brand\tLocation\tTime the brand is at screen\tDuration\tSolus\tScreen Location\tScreen Size %\tTotal Hits\tAverage Hits\tSequence Frame Number\n";
    "news" == b && (c = "Brand\tLocation\tChannel\tDate\tDuration\tSolus\tScreen Location\tScreen Size %\tTotal Hits\tAverage Hits\tSequence Frame Number\n");
    var e = {},

        g = Object.keys(allAnnotations.images),
        l = g.length;
    g.sort(alphanumCase);
    for (var m = 0; m < l; m++) {
        var B = g[m],
            r = allAnnotations.images[B],
            x = "",
            q = "",
            p = "";
        if ("news" == b)
            for (var d = B.split("_"), h = 0, s = d.length - 1; h <= s; h++)
                if (isNaN(parseInt(d[h]))) x = d[h];
                else if (5 < d[h].length) {
            var q = "dd",
                n = "mm",
                t = "yy";
            6 <= d[h].length && (q = d[h].substr(0, 2), n = d[h].substr(2, 2), 12 < parseInt(d[h].substr(2,
                2)) && (q = d[h].substr(2, 2), n = d[h].substr(0, 2)), t = 8 == d[h].length ? d[h].substr(4, 4) : d[h].substr(4, 2));
            q = q + "/" + n + "/" + t
        } else p = d[h];
        for (var d = r.width, s = r.height, n = d * s, t = r.annotations, y = 1 < t.length ? 0 : 1, r = parseInt(B) || r.imageIndex, v = secsToHour24((f + r) % 43200), u = {}, h = 0, C = t.length; h < C; h++) {
            var z = t[h].brand,
                w = t[h].tpoint,
                D = t[h].hits,
                A = t[h].startPoint,
                E = t[h].diagPoint,
                G = checkImagePart(d, s, A[0] + Math.round((E[0] - A[0]) / 2), A[1] + Math.round((E[1] - A[1]) / 2)),
                F = Math.abs(E[0] - A[0]),
                A = Math.abs(E[1] - A[1]),
                F = Math.round(F * A /
                    n * 1E5) / 1E3;
            u[z + "::" + w] = {
                brand: z,
                tpoint: w,
                time: v,
                duration: 1,
                solus: y,
                location: G,
                size: F,
                hits: D,
                avgHits: D / 1,
                frameNum: B,
                annoTimeOffset: r,
                channel: x,
                date: q,
                newsId: p
            }
        }
        for (var k in e) !u.hasOwnProperty(k) || 1 < Math.abs(r - e[k].annoTimeOffset) || q !== e[k].date || x !== e[k].channel ? (a[e[k].time + "::" + e[k].brand + "::" + e[k].tpoint] = e[k], delete e[k]) : (e[k].annoTimeOffset = r, e[k].duration += 1, e[k].hits += u[k].hits, e[k].avgHits = Math.round(e[k].hits / e[k].duration * 10) / 10, delete u[k]);
        for (k in u) e[k] = u[k]
    }
    if (0 !== Object.keys(e).length)
        for (k in e) a[e[k].time +
            "::" + e[k].brand + "::" + e[k].tpoint] = e[k], delete e[k];
    k = Object.keys(a);
    f = k.length;
    k.sort(alphanumCase);
    for (m = 0; m < f; m++) e = k[m], c = "news" == b ? c + (a[e].brand + "\t" + a[e].tpoint + "\t" + a[e].channel + "\t" + a[e].date + "\t" + a[e].duration + "\t" + a[e].solus + "\t" + a[e].location + "\t" + a[e].size + "\t" + a[e].hits + "\t" + a[e].avgHits + "\t" + a[e].newsId + "\n") : c + (a[e].brand + "\t" 
	+ a[e].tpoint + "\t" 
	+ a[e].time + "\t" 
	+ a[e].duration + "\t" + 
	//a[e].solus + "\t" 
	+ a[e].location + "\t" 
	+ a[e].size + "\t" 
	+ a[e].hits + "\t" 
	+ a[e].avgHits + "\t" + (parseInt(a[e].frameNum) ||
        a[e].frameNum) + "\n");
	
	window.URL = window.webkitURL || window.URL;
	var contentType = 'text/csv';
	var csvFile = new Blob([c], {type: contentType});
	saveAs(csvFile, allAnnotations.project.replace(/ /g,'_').replace(/---|--/g,'-') + "-" + allAnnotations.Annotator + "-" + timestamp() + "-News.csv"); //v24.8
}

function generateNewsCSV_3(){ //from video.csv
	if(""==$("#AnnotatorName").html()){alert("please enter annotator name !");return!1};
	var a=[];$("#generateNewsCSV").blur();
	if(""==$("#projectFolder").val())return!1;
	storeAnnotationImg();
	
	var hm=allAnnotations.project.split("_"),
	hm=hm[hm.length-1]||"0000", // gives 4 last digits OR 0000 if hm is false
	c=isNaN(hour24ToSecs(hm))?0:hour24ToSecs(hm), //gives hm time to seconds OR 0 if no time available
	
	b="Brand\tLocation\tFileName\tDuration\tSolus\tScreen Location\tScreen Size %\tTotal Hits\tAverage Hits\tSequence Frame Number\n",
	d={},
	e=Object.keys(allAnnotations.images),
	g=e.length;
	e.sort(alphanumCase);

	for(var f=0;f<g;f++){
		for(var h=e[f], //gives filename
			k=allAnnotations.images[h],
			C=k.width,
			v=k.height,
			z=C*v,
			p=k.annotations,
			n=1<p.length?0:1, //defines 0 or 1 for solus
			k=parseInt(h)||k.imageIndex, //filename to integer
			r=secsToHour24(c+k),
			q={},
			l=0,
			A=p.length;
			l<A;
			l++
			)
		{
			var y=p[l].brand,
			s=p[l].tpoint,
			w=p[l].hits,
			u=p[l].startPoint,
			x=p[l].diagPoint,
			t=checkImagePart(C,v,u[0]+Math.round((x[0]-u[0])/2),
			
			u[1]+Math.round((x[1]-u[1])/2)),
			B=Math.abs(x[0]-u[0]),
			u=Math.abs(x[1]-u[1]),
			B=Math.round(B*u/z*1E5)/1E3;q[y+"::"+s]={brand:y,tpoint:s,time:r,duration:1,solus:n,location:t,size:B,hits:w,avgHits:w/1,frameNum:h,annoTimeOffset:k}
		}
	for(var m in d)!q.hasOwnProperty(m)||1<Math.abs(k-d[m].annoTimeOffset)?(a[d[m].time+"::"+d[m].brand+"::"+d[m].tpoint]=d[m],delete d[m]):(d[m].annoTimeOffset=k,d[m].duration+=1,d[m].hits+=q[m].hits,d[m].avgHits=Math.round(d[m].hits/d[m].duration*10)/10,delete q[m]);
	for(m in q)d[m]=q[m]}m=Object.keys(a);
	c=m.length;m.sort(alphanumCase);
	for(f=0;f<c;f++)d=m[f],b+=a[d].brand+"\t"+a[d].tpoint+"\t"
	+a[d].frameNum.split('_')[0]+"_"+a[d].frameNum.split('_')[1]+"_"+a[d].frameNum.split('_')[2]+"\t"
	+a[d].duration+"\t"
	//+a[d].solus+"\t"+
	a[d].location+"\t"
	+a[d].size.toFixed(3)+"\t"+a[d].hits+"\t"+a[d].avgHits+"\t"+
	(parseInt(a[d].frameNum.split('_').pop().toString())||a[d].frameNum.split('_').pop().toString())+"\n";
	
	window.URL = window.webkitURL || window.URL;
	var contentType = 'text/csv';
	var csvFile = new Blob([b], {type: contentType});
	saveAs(csvFile, allAnnotations.project.replace(/ /g,'_').replace(/---|--/g,'-') + "-" + allAnnotations.Annotator + "-" + timestamp() + "-News.csv"); //v24.8
}

function generateAnnFilesZip() {
	if(""==$("#AnnotatorName").html()){alert("please enter annotator name !");return!1};
    $("#generateAnnFiles").blur();
    if ("" == $("#projectFolder").val()) return !1;
    storeAnnotationImg();
    for (var a = new JSZip, b = 0, c = imIndices.length; b < c; b++) {
        var d = imIndices[b],
            e = "";
        if (allAnnotations.images.hasOwnProperty(d))
            for (var g = allAnnotations.images[d].width * allAnnotations.images[d].height, f = allAnnotations.images[d].annotations, h = 0, k = f.length; h < k; h++) var C = f[h].brand,
                v = f[h].tpoint,
                z = f[h].hits,
                p = f[h].startPoint,
                n = f[h].diagPoint,
                r = Math.abs(n[0] - p[0]),
                q = Math.abs(n[1] - p[1]),
                r = Math.round(r * q / g * 1E5) / 1E3,
                e = e + ("#:" + C + ":" + v + ":" + Math.round(p[0]) + "," + Math.round(p[1]) + "," + Math.round(n[0]) + "," + Math.round(n[1]) + ":" + r + ":" + z + "\n");
        a.file(d + ".ann", e)
    }
    a = a.generate({
        type: "blob"
    });
    saveAs(a, allAnnotations.project.replace(/ /g,'_').replace(/---|--/g,'-') + "-" + allAnnotations.Annotator + "-" + timestamp() + "-ann.zip");
}

function videoALL(){ //unused
	downloadAnnotations();
	generateVideoCSV();
}