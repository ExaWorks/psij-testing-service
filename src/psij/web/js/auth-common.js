function genericSubmit(vue, path, params, successMessage, crtReCaptcha) {
    vue.requestSubmitDialog = true;
    if (crtReCaptcha) {
        grecaptcha.reset(crtReCaptcha);
    }
    $.post(PS.getURL(path), params, function(data) {
        vue.requestSubmitDialog = false;
        if (!data) {
            vue.showErrorDialog("Server did not return any data. Please try again later.");
        }
        else if (!data.success) {
            if (data.bannedDomain) {
                vue.showBannedDomainDialog(data.domain, data.email);
            }
            else {
                vue.showErrorDialog(data.error);
            }
        }
        else {
            vue.showSuccessDialog(successMessage);
        }
    }).fail(function(jqXHR, textStatus, errorThrown) {
        console.log(jqXHR.responseText);
        vue.requestSubmitDialog = false;
        vue.showErrorDialog("An unknown error has occurred. Please try again later.");
    });
}