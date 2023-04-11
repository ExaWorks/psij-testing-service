var PS = PS || {};

PS.sites = [
];

var settingsDefaults = settingsDefaults || function() {};

settingsDefaults({"viewMode": "calendar", "inactiveTimeout": 10, "showBranchBubbles": false});

PS.getURL = function( path ) {
    return CONF.backendURL + path;
};
