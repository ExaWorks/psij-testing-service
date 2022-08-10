var sites = [
];

settingsDefaults({"viewMode": "calendar", "inactiveTimeout": 10, "showBranchBubbles": false});

set = function(dst, src) {
    dst.length = 0;
    for (var i = 0; i < src.length; i++) {
        dst.push(src[i]);
    }
}

update = function() {
    $.get("summary", settings("inactiveTimeout"), function(data) {
        set(sites, data);
    });
};

update();

var siteStatus = new Vue({
    el: "#container",
    components: {
        'intro-blurb':VC.IntroBlurb
    },
    vuetify: new Vuetify(),
    data: {
        sites: sites,
        mode: '',
        now: moment().utc().startOf("day"),
        settingsDialog: false,
        STR: CONF.STR
    },
    methods: globalMethods,
    computed: {
        inactiveTimeout: makeSetting("inactiveTimeout", update),
        showBranchBubbles: makeSetting("showBranchBubbles", update, "bool"),
        allBranches: function() {
            var unique = {};
            for (var i = 0; i < this.sites.length; i++) {
                var site = this.sites[i];
                var branches = site.branches;
                for (var j = 0; j < branches.length; j++) {
                    var branch = branches[j];
                    if (branch.name in unique) {
                        var existing = unique[branch.name];
                        existing['failed_count'] += branch['failed_count'];
                        existing['completed_count'] += branch['completed_count'];
                    }
                    else {
                        unique[branch.name] = {... branch};
                        unique[branch.name]['sites'] = {};
                    }
                    unique[branch.name]['sites'][site.site_id] = branch;
                }
            }

            values = [];
            for (var k in unique) {
                values.push(unique[k]);
            }
            return this.sort('name', values);
        },
        branchIndexMap: function() {
            var all = this.allBranches;
            var map = {};
            for (var i = 0; i < all.length; i++) {
                map[all[i].name] = i;
            }
            return map;
        }
    }
});

var setViewMode = function(viewMode) {
    if (viewMode === undefined) {
        viewMode = Cookies.get('viewMode');
    }
    if (viewMode === undefined) {
        viewMode = 'calendar';
    }
    Cookies.set('viewMode', viewMode);
    $('.view-mode-group').removeClass('selected');
    $('#view-mode-' + viewMode).addClass('selected');
    siteStatus.mode = viewMode;
}

setViewMode();

