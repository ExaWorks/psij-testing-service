//  lib.js
var PS = PS || {};
const SiteState = {
    // All tests passed
    AllPassed: 1,
    // Some but not more than half of tests failed
    SomeFailed: 2,
    // More than half of tests failed
    MostFailed: 3,
    // There are two or fewer tests (setup an teardown), meaning no actual tests ran
    RunFailed: 4,
    // No data at all
    NoResults: 5
};

const GroupState = {
    // All sites passed all tests
    AllPassed: 1,
    // Some sites have some failures
    SomeFailed: 2,
    // Some sites are missing, but the rest are all passin
    MissingAndPassed: 3,
    // Some sites are missing and some of the rest are failing
    MissingAndFailed: 4,
    // All missing
    NoResults: 5
};

const TestResult = {
    Unknown: 0,
    Passed: 1,
    Failed: 2,
    Skipped: 3
};

var badness = function(obj) {
    if( obj['completed_count'] === 0 ) {
        return SiteState.NoResults;
    }

    if( obj['completed_count'] <= 2 ) {
        return SiteState.RunFailed;
    }

    if (obj['failed_count'] > 0 ) {
        if (obj['completed_count'] < obj['failed_count'] ) {
            return SiteState.MostFailed;
        }
        else {
            return SiteState.SomeFailed;
        }
    }

    return SiteState.AllPassed;
};

var urlParam = function(paramName) {
    var p = new URLSearchParams(window.location.search);
    return p.get(paramName);
}

var getDayData = function(site, day) {
    if (day.month_num in site["months"]) {
        var month = site["months"][day.month_num];
        if (day.day in month) {
            return month[day.day];
        }
    }
    return {branches:[]};
}

var getBranchData = function(branch, dayData) {
    if (branch == null) {
        return dayData;
    }
    var name = branch.name;
    if (dayData != null) {

        for (var i = 0; i < dayData.branches.length; i++) {
            if (dayData.branches[i].name == name) {
                return dayData.branches[i];
            }
        }
    }
    return null;
}

var settingsDefaults = function(dict) {
    for (var k in dict) {
        var val = localStorage.getItem(k);
        if (val == undefined) {
            localStorage.setItem(k, dict[k]);
        }
    }
};

var setting = function(name, type) {
    var val = localStorage.getItem(name);

    if (type == "bool") {
        return val == "true";
    }
    else {
        return val;
    }
}


var makeSetting = function(name, callback, type) {
    return {
        get: function() {
            return setting(name, type);
        },

        set: function(val) {
            localStorage.setItem(name, val);
            if (callback) {
                callback(name, val);
            }
        }
    }
};

var settings = function(...names) {
    var obj = {};
    for (var i = 0; i < names.length; i++) {
        var name = names[i];
        var type = null;
        if (name.includes(":")) {
            var s = name.split(/:/);
            name = s[0];
            type = s[1];
        }
        obj[name] = setting(name, type);
    }

    return obj;
};

var ansi_up = new AnsiUp();
ansi_up.use_classes = true;


var globalMethods = {
    sort: function(key, lst) {
        if (!lst) {
            return lst;
        }
        return lst.slice().sort((a, b) => {
            var av = a[key];
            var bv = b[key];
            return av > bv ? 1 : (av == bv) ? 0 : -1;
        });
    },
    sitesSort: function(sites) {
        var copy = sites.slice();
        for (var i = 0; i < copy.length; i++) {
            var site = copy[i];
            site.key = site.site_id.split('.').reverse().join('.');
        }
        strComp = function(a, b) {if (a > b) return 1; else if (a == b) return 0; else return -1;};

        return copy.sort((a, b) => strComp(a.key, b.key));
    },
    limit: function(array, n) {
        if (array.length > n) {
            return array.slice(0, n);
        }
        else {
            return array;
        }
    },
    /**
     * Returns a CSS class that represents the state of the tests on siteState, which can
     * be either an instance of the SiteState enum or a site object.
     */
    siteStateCSSClass: function(siteState) {
        if (!Number.isInteger(siteState)) {
            siteState = badness(siteState);
        }
        switch(siteState) {
            case SiteState.AllPassed:
                return "state-good";
            case SiteState.SomeFailed:
                return "state-somewhat-bad";
            case SiteState.MostFailed:
            case SiteState.RunFailed:
                return "state-really-bad";
            case SiteState.NoResults:
                return "state-empty";
        }
    },
    groupStateCSSClass: function(groupState) {
        switch(groupState) {
            case GroupState.AllPassed:
                return "state-good";
            case GroupState.SomeFailed:
                return "state-really-bad";
            case GroupState.MissingAndPassed:
                return "state-missing-and-good";
            case GroupState.MissingAndFailed:
                return "state-missing-and-bad";
            case GroupState.NoResults:
                return "state-empty"
        }
    },
    branchCSSClass: function(branchName) {
        return branchName == "main" || branchName == "master" ? "bubble-large" : "bubble-small";
    },
    badnessSort: function(lst) {
        return lst.slice().sort((a, b) => {
            return badness(a) - badness(b);
        });
    },
    branchSort: function(lst) {

        if (localStorage.getItem("showBranchBubbles") != "true") {
            return lst.filter(branch => (branch.name == "main") || (branch.name == "master"));
        }
        var sorted = lst.slice().sort((a, b) => {
            if (a.name == "main" || a.name == "master") {
                // main goes first
                return -1;
            }
            if (b.name == "main" || b.name == "master") {
                return 1;
            }
            return a.name.localeCompare(b.name);
        });
        return sorted;
    },
    //  could be more optimized
    isSingleUrl: function( url ) {

        var count = 0;
        var test_domain = this.getDomain( url );

        for( var x in this.sites ) {

            var site = this.sites[x];
            var loop_domain = this.getDomain( site.site_id );

            if( test_domain === loop_domain ) {
                count++;
            }
        }

        console.dir( this.sitesSort(this.sites) );
        console.log( test_domain + count );
        return count < 2;
    },
    getPosition: function( url ) {

        if( this.isSingleUrl(url) ) {
            return 'oneRowOnly';
        }

        var domain = globalMethods.getDomain( url );
        PS.urls = PS.urls || {};

        PS.urls[domain] = PS.urls[domain] || 0;
        PS.urls[domain]++;

        if( PS.urls[domain] <= 2 ) {
            return "firstPos";
        }

        return "otherPos";
    },
    getDomain: function( url ) {

        var uparts = url.split('.');
        var len = uparts.length;
        var first = uparts[len - 2];
        var first_dot = first ? (first + '.') : "";

        return first_dot + uparts[len - 1];
    },
    navigate: function(loc) {
        //console.log(loc);
        return "event.stopPropagation(); window.location=\"" + loc + "\"";
    },
    shortenId: function(id) {
        if (id === undefined) {
            return "###";
        }
        else {
            return id.slice(-6);
        }
    },
    testStatus: function(test) {
        var results = test.results;
        if (results === undefined) {
            return TestResult.Unknown;
        }
        var passed = true;
        var skipped = false;
        for (var k in results) {
            passed &&= results[k].passed;
            if (k == "call") {
                skipped = (results[k].status == "skipped");
            }
        }

        if (passed) {
            return TestResult.Passed;
        }
        else if (skipped) {
            return TestResult.Skipped;
        }
        else {
            return TestResult.Failed;
        }
    },
    testStatusText: function(test) {
        switch(this.testStatus(test)) {
            case 0:
                return "Unknown";
            case 1:
                return "Passed";
            case 2:
                return "Failed";
            case 3:
                return "Skipped";
        }
    },
    testStatusIcon: function(test) {
        switch(this.testStatus(test)) {
            case 0:
                return "help";
            case 1:
                return "check_circle";
            case 2:
                return "cancel";
            case 3:
                return "indeterminate_check_box";
        }
    },
    testStatusClass: function(test) {
        switch(this.testStatus(test)) {
            case 0:
                return "test-status-unknown";
            case 1:
                return "test-status-passed";
            case 2:
                return "test-status-failed";
            case 3:
                return "test-status-skipped";
        }
    },
    formatEnvValue: function(key, value) {
        switch(key) {
            case "run_id":
                return '<span title="' + value + '">...' + this.shortenId(value) + '</span>';
            case "git_last_commit":
                return value.slice(1, -1);
            case "stdout":
            case "stderr":
            case "log":
                if (value === "") {
                    return '<span class="material-icons env-missing-value">cancel</span>'
                }
                else {
                    return '<div class="listing listing-text listing-log">' + value + '</div>';
                }
            case "git_local_change_summary":
                return '<div class="listing listing-text"> ' + value + '</div>';
            case "results":
            case "extras":
                if (value === "") {
                    return '<span class="material-icons env-missing-value">cancel</span>'
                }
                else {
                    return '<div class="listing listing-json">' + JSON.stringify(value, null, 4) + '</div>';
                }
            case "executors":
            case "computed_executors":
                if (typeof value === "string") {
                    value = value.split(",");
                }
                var s = "";
                for (var i = 0; i < value.length; i++) {
                    s += '<span class="executor-name">' + value[i] + '</span>';
                }
                return s;
            default:
                if (value === "") {
                    return '<span class="material-icons env-missing-value">cancel</span>'
                }
                else {
                    return value;
                }
        }
    },
    hasReport: function(test) {
        if ("call" in test.results) {
            var report = test.results["call"]["report"];
            if (report !== undefined && report.length > 0) {
                return true;
            }
        }
        return false;
    },
    renderReport: function(test) {
        if ("call" in test.results) {
            var report = test.results["call"]["report"];
            return ansi_up.ansi_to_html(report);
        }
        else {
            return "";
        }
    },
    daysRange: function(now, ndays) {
        var days = [];
        var crt = moment(now);
        crt.add(-ndays + 1, "days");
        var change = false;
        for (var i = 0; i < ndays; i++) {
            var day = crt.date();
            var entry = new Object();
            days.push(entry);
            entry.day = day;
            entry.monthChange = false;
            entry.cls = "month-none";
            entry.month_num = crt.month() + 1;
            if (day == 1) {
                entry.monthChange = true;
                if (i > 0) {
                    crt.add(-1, "days");
                    days[i - 1].month = crt.format("MMMM");
                    crt.add(1, "days");
                }
                days[i].month = crt.format("MMMM");
                change = true;
            }
            crt.add(1, "days");
        }
        if (!change) {
            days[0].month = crt.format("MMMM");
        }
        return days;
    },
    calendarBubbleClass: function(site, day, branch) {
        var size = function(branch) {
            return branch.name == "main" || branch.name == "master" ? "bubble-large" : "bubble-small";
        }
        var d = getBranchData(branch, getDayData(site, day));
        if (d == null || (d.completed_count == 0 && d.failed_count == 0)) {
            return "state-unknown " + size(branch);
        }
        else {
            return this.badnessClass(d); // + ", " + size(branch);
        }
    },
    calendarBubbleStyle: function(site, day, branch) {

        var d = getBranchData(branch, getDayData(site, day));
        return globalMethods.calendarBubbleStyleObj(d);
    },
    calendarBubbleStyleObj: function( d ) {
        var color;
        if (d != null) {
            var completed = d.completed_count;
            var failed = d.failed_count;

            if (completed == 0 && failed == 0) {
                color = "#f0f0f0";
            }
            else if (completed > 0 && failed > completed / 2) {
                // real bad
                color = "#ff4d4d";
            }
            else if (failed == 0) {
                // no failures
                color = "#6aff4d";
            }
            else {
                // less than half failures
                var h = 0.20 - failed / completed * 2 * 0.20;
                var s = 0.7;
                var v = 0.95;

                var region = Math.floor(h * 6);
                var f = h * 6 - region;
                var p = v * (1 - s);
                var q = v * (1 - f * s);
                var t = v * (1 - (1 - f) * s);

                var r, g;
                var b = p;
                if (region == 0) {
                    r = v;
                    g = t;
                }
                else {
                    r = q;
                    g = v;
                }
                color = "rgba(" +
                    (r * 255).toFixed() + ", " +
                    (g * 255).toFixed() + ", " +
                    (b * 255).toFixed() + ")";
            }
        }
        else {
            color = "#e0e0e0";
        }

        return "background-color: " + color;
    },
    getDayData: getDayData,
    breadcrumbs: function() {

        var projName = CUSTOMIZATION.projectName;

        var b = [{text: projName + " Tests", href: "summary.html"}];
        var level = 0;
        if (window.location.pathname.startsWith("/site.html")) {
            level = 1;
        }
        if (window.location.pathname.startsWith("/run.html")) {
            level = 2;
        }
        if (level >= 1) {
            b.push({
                text: "Site " + this.site.site_id,
                href: "/site.html?site_id=" + this.site.site_id
            })
        }
        if (level >= 2) {
            b.push({text: "Run " + this.shortenId(this.run.run_id)})
        }
        return b;
    },
    updateRender: function() {
        this.$forceUpdate();
    },
    setting: setting
}

$(document).ready(function() {

    setTimeout(function() {

        $('.clickable').each(function() {
            if ($(this).attr('onclick') !== undefined) {
                var v = $(this).attr('onclick');
                var ix = v.indexOf('window.location=');
                if (ix != -1) {
                    $(this).attr('title', v.slice(ix + 17, -1));
                }
            }
        });
    }, 500);
});
