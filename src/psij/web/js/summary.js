var siteStatus;

var setViewMode = function (viewMode) {
    if (viewMode === undefined) {
        viewMode = localStorage.getItem('viewMode');
    }
    if (viewMode === undefined) {
        viewMode = 'calendar';
    }

    localStorage.setItem('viewMode', viewMode);

    $('.view-mode-group').removeClass('selected');
    $('#view-mode-' + viewMode).addClass('selected');

    siteStatus.mode = viewMode;
};

var Summary = function() {

    /**
     * placeholders that are used because sometimes we update one without the other and
     * we need both for some calculation.
     */
    var sites = [];
    var tests = [];

    var today = moment().utc().startOf("day");
    /**
     * Copies all elements from src to dst, truncating dst first. This is used to
     * set a Vue reactive property that is array valued.
     */
    var copyToArray = function(dst, src) {
        dst.length = 0;
        for (var i = 0; i < src.length; i++) {
            dst.push(src[i]);
        }
    };

    var update;
    var updateSetting;

    var siteStatus = new Vue({
        el: "#container",
        components: {
        },
        vuetify: new Vuetify(),
        data: {
            sites: sites,
            testsHeader: [],
            testsItems: [],
            calendarHeader: [],
            calendarItems: [],
            mode: '',
            now: today,
            settingsDialog: false,
            calendarLoading: false,
            settings: settings("showBranchBubbles:bool", "showAllRows:bool")
        },
        methods: globalMethods,
        computed: {
            inactiveTimeout: makeSetting("inactiveTimeout", function() {update()}, validatePositiveInt),
            showBranchBubbles: makeSetting("showBranchBubbles",
                function(name, value) {updateSetting(name, value)}, "bool"),
            showAllRows: makeSetting("showAllRows",
                function(name, value) {updateSetting(name, value)}, "bool")
        }
    });

    sitesUpdated = function(data) {
        copyToArray(sites, data);
        copyToArray(siteStatus.calendarHeader, globalMethods.getCalendarHeader(sites, today, 8));
        copyToArray(siteStatus.calendarItems, globalMethods.getCalendarItems(sites, today, 8));
    };

    update = function() {
        siteStatus.calendarLoading = true;
        $.get(PS.getURL("summary"), settings("inactiveTimeout"), function(data) {
            sitesUpdated(data);
            siteStatus.calendarLoading = false;
        });
    };

    updateSetting = function(name, value) {
        siteStatus.settings[name] = value;
        if (name == "showBranchBubbles") {
            // we also need to recalculate table data
            sitesUpdated(sites);
        }
    };

    update();


    return siteStatus;
};

siteStatus = Summary();
setViewMode();
