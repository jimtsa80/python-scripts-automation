
function annoDataTable(){
	$('table#allAnnos').DataTable( {
		dom: 'Blfrtipr',
		"lengthMenu": [[20, 50, 100, -1], [20, 50, 100, "All"]],
		"iDisplayLength": -1,
		"order": [[ 1, 'asc' ], [ 2, 'asc' ]],
		columnDefs: [ 
			{ className: 'select-checkbox',	orderable: false, targets: 0 },
		],
		select: {
            style:    'os',
            selector: 'td:first-child'
        },
		buttons: [
            {
                text: 'delete',
                action: function (  ) {
                    alert( 'delete selected annos ( under construction )' );
					// delete allAnnotations.images[imName]
                }
            }
        ]
	});
}

function tpfltrdata(){
	if ( $('table#tbl_tpfltr').html()!=="" ) { 
		$('table#tbl_tpfltr').DataTable().destroy(); 
	}
	var dataSet = []; 
	for (i in prefs.tpoints){
		for (y in prefs.conns){
			if ( prefs.conns[y].tpoints.indexOf(prefs.tpoints[i])>-1 ) {
				dataSet.push( [ prefs.tpoints[i], prefs.conns[y].brand, prefs.conns[y].group ])
			}
		}
	}
	dataSet.sort()
	var table = $('#tbl_tpfltr').DataTable( {
        data: dataSet,
		dom: '<"toolbar">frtip',
        columns: [
            { title: "touchpoint" },
            { title: "brand" },
            { title: "group" }
        ],
		
		initComplete: function () {
            this.api().columns().every( function () {
                var column = this;
                var select = $('<select><option value=""></option></select>')
                    .prependTo( $(column.header()).empty() )
                    .on( 'change', function () {
                        var val = $.fn.dataTable.util.escapeRegex(
                            $(this).val()
                        );
 
                        column
                            .search( val ? '^'+val+'$' : '', true, false )
                            .draw();
                    } );
 
                column.data().unique().sort().each( function ( d, j ) {
                    select.append( '<option value="'+d+'">'+d+'</option>' )
                } );
            } );
        }
		
    } );
	
	// $('#tbl_tpfltr_wrapper').width($('#tbl_tpfltr').width())
}

 