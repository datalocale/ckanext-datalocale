var json_data = {"Departements" : "","Cantons" : "","Communes" : ""}
var json_label = {"Departements": new Array("code-dept","code-dept","nom-dept"), "Cantons": new Array("code-dept","code-canton","nom-chf"),"Communes": new Array("code-dept","code-comm","nom-comm") }

  $(function() {
    $("#themeTaxonomy").each(function () {
      getThemeTag($(this).val());
    });

    $("#themeTaxonomy").change(function(){
        getThemeTag($(this).val());
    });
    $("#spatial_type").each(function () {
      getSpatial($(this).val());
    });

    $("#spatial_type").change(function(){
        getSpatial($(this).val());
    });

    $("#spatial_Departements").change(function(){
        if($("#spatial_type").val() == "Communes") {spatialPopulateCommune($(this).val());}
    });

    $('#generate-extent').click(function (event) 
    { 
      event.preventDefault(); 
      type = $("#spatial_type").val();
      getExtent($("#spatial_"+type).val());

    });
	/**	Gestion du datepicker */
    $("#temporal_coverage-from").datepicker({ minDate: new Date(2011, 1 - 1, 1), changeMonth: true, onSelect: function( selectedDate ) {
	$( "#temporal_coverage-to" ).datepicker( "option", "minDate", selectedDate );} });
    $("#temporal_coverage-to").datepicker({ minDate: new Date(2011, 1 - 1, 1), changeMonth: true, onSelect: function( selectedDate ) {
	$( "#temporal_coverage-from" ).datepicker( "option", "maxDate", selectedDate );} });
    $('#temporal_coverage-from').datepicker('option', 'dateFormat', 'dd/mm/yy');
    $('#temporal_coverage-from').datepicker("setDate", new Date(temporal_coverage_from));
    $('#temporal_coverage-to').datepicker('option', 'dateFormat', 'dd/mm/yy');
    $('#temporal_coverage-to').datepicker("setDate", new Date(temporal_coverage_to));
  });	

  /**	Spatial : Récupérer les données (.json) **/
  function getSpatial(type_id) {
    if(type_id != "") {
      if(type_id == "Communes") {getSpatial("Departements");}
      if(json_data[type_id] != "") {if(type_id=="Communes") {spatialPopulateCommune($("#spatial_Departements").val());} else {spatialPopulate(type_id);} return;}
      $.ajax({
        dataType: 'text',
        success: function(string) {
          data = $.parseJSON(string);
	  json_data[type_id]  =data;; 
	  if(type_id=="Communes") {
	    spatialPopulateCommune($("#spatial_Departements").val());
	  }
	  else {
            spatialPopulate(type_id);
	  }
        },
        url: '/data/'+type_id+'.json'
      });
    }
  }

  /**	Spatial : Remplir les combobox **/
  function spatialPopulate(type_id) {
    // Compléter les combobox
    data = json_data[type_id]
    spatialFillCombobox(data.features, type_id)
  }

    /**	Spatial : Remplir la combobox "Communes" **/
  function spatialPopulateCommune(departement_id) {
    data = json_data["Communes"]
    data_filter = jQuery.grep(data.features, function(element, index){
	  return element.properties['code-dept'] == departement_id;
    });
    spatialFillCombobox(data_filter,"Communes");
  }

    /**	Spatial : Remplir une combobox **/
  function spatialFillCombobox(data_filter, type_id) {
    html = ""
    //Afficher les combobox
    for (key in json_data) 
    {
       if(key == type_id)
         $("#spatial_"+key).show()
       else
         $("#spatial_"+key).hide()
    }
    if(type_id == "Communes")
       $("#spatial_Departements").attr("style","") 
    for(item in data_filter) {
	value = data_filter[item].properties[json_label[type_id][1]]
	label = data_filter[item].properties[json_label[type_id][2]]
	geometry = data_filter[item].geometry
        if(data_filter[item].properties.uri == selected_spatial_uri) {
          html += '<option value="'+ value+'" selected="selected">'+value+' - '+ label+'</option>'
	}
	else {
          html += '<option value="'+ value+'">'+value+' - '+ label+'</option>'
	}
     }
   $("#spatial_"+type_id).html(html);
   sortDropDownListByText("#spatial_"+type_id)
  }
  /**	Spatial : Calculer les extents **/
  function getExtent(value) {
     type_id = $('#spatial_type').val();
     obj = json_data[type_id]
     label = json_label[type_id][1]
     extent = jQuery.grep(obj.features, function(element, index){
	  return element.properties[label] == value;
     });
     extent_value = extent[0].geometry.coordinates;
     extent_text = extent[0].properties[json_label[type_id][2]];
     extent_uri = extent[0].properties.uri;
     $("#spatial").val('{"type":"Polygon","coordinates":'+extent_value+'}') ;
     $("#spatial-text").val(extent_text) ;
     $("#spatial-uri").val(extent_uri) ;
  }

  /**	Thèmes : Récupérer les données **/
  function getThemeTag(id) {
    html = '<div class="controls" id="theme" name="theme">Actualisation en cours</div>'
    $("#theme").replaceWith(html);
    if(id!="") {
      jQuery.ajax({
        type: 'POST',
        url: api_url+'/fr/api/3/action/datalocale_vocabulary_list',
        contentType : 'application/json;charset=utf-8',
        dataType: 'json',
        data: '{"id": "'+id+'"}',
        success: successfulQuery,
        error: unsuccessfulQuery,
      });
    }
    else {
      successfulQuery(null)
    }
  }

  /**	Thèmes : Afficher les données **/
  function successfulQuery(data) {
    html = '<div class="controls" id="theme" name="theme"><select class="chzn-select" id="theme_available" name="theme_available">'
    if(data!=null) {
      tags = data['result'];
      tags.sort(function (a, b) {
        a = a[1],
        b = b[1];
        return a.localeCompare(b);
      });
      for (tag in tags) {
        if(selected_theme == tags[tag][0])  {
          html += '<option selected="selected" value="'+ tags[tag][0]+'">'+ tags[tag][1]+'</option>'}
        else {
          html += '<option value="'+ tags[tag][0]+'">'+ tags[tag][1]+'</option>'}
      }
    }
    else {
      html += '<option value="">(Aucun)</option>'
    }
    html += "</select></div>"
    $("#theme").replaceWith(html);
  }

  /**	Thèmes : Afficher les données **/
  function unsuccessfulQuery(data) {}
    

  /**	Shared : Trier les combobox **/
  function sortDropDownListByText(combobox_id) {
    // Loop for each select element on the page.
    $(combobox_id).each(function() {
        // Keep track of the selected option.
        var selectedValue = $(this).val();
        // Sort all the options by text. I could easily sort these by val.
        $(this).html($("option", $(this)).sort(function(a, b) {
            return a.text == b.text ? 0 : a.text < b.text ? -1 : 1
        }));
        // Select one option.
        $(this).val(selectedValue);
    });
  }
