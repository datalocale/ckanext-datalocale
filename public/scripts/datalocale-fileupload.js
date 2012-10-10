	$('#file_upload').fileupload({
	    url: '/storage/datalocale_upload_handle',
	    type: 'POST',
	    done: function (e, data) {
	    	$('#image_url').val(data.result);
	    	alert("Votre image a été envoyé et enregistré sur le serveur.");
	    },
	    fail: function (e, data) {
	    	$('#image_url').val("");
	    	alert("Une erreur est survenue lors du téléchargement de votre image.");
	    }
	});