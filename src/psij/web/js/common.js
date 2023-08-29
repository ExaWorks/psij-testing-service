var PS = PS || {};

settingsDefaults({
    "viewMode": "calendar",
    "inactiveTimeout": 10,
    "showBranchBubbles": false,
    "showAllRows": false
});

PS.getURL = function( path ) {
    return CUSTOMIZATION.backendURL + path;
};
