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

const TLDOrder = {
    "gov": 4,
    "edu": 3,
    "org": 2,
    "net": 1,
    "*": 0
};

var getBackendURL = function(path) {
    return CUSTOMIZATION.backendURL + path;
};

var getTLDIndex = function(tld) {
    if (tld in TLDOrder) {
        return TLDOrder[tld];
    }
    else {
        return TLDOrder["*"];
    }
}

PS.TestResult = TestResult;
PS.SiteState = SiteState;

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
            var rparts = site.site_id.split(".").reverse();
            site.tld = rparts[0];
            site.rest = rparts.slice(1).join(".");
        }
        tldComp = function(a, b) {return getTLDIndex(b) - getTLDIndex(a)};

        /* compare known TLDs first; if neither are known TLDs, compare TLDs lexicographically,
           and, finally, compare the remainder of the reverse FQDN lexicographically. */
        return copy.sort((a, b) => tldComp(a.tld, b.tld) || a.tld.localeCompare(b.tld) ||
            a.rest.localeCompare(b.rest))
    },
    groupIndex: function(domain) {
        var rparts = domain.split('.').reverse();
        var tld = rparts[0];
        if (tld in TLDOrder) {
            rparts[0] = TLDOrder[tld] + "-" + tld;
        }
        else {
            rparts[0] = TLDOrder["*"] + "-" + tld;
        }
        return rparts.join(".");
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
    getDomain: function(url) {
        var uparts = url.split(".");
        if (uparts.length < 2) {
            return url;
        }
        else {
            return uparts.at(-2) + "." + uparts.at(-1);
        }
    },
    navigate: function(loc) {
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
    /**
     * Returns the header for the calendar table starting at day <code>start</code> and
     * having <code>ndays</code> columns. The header is returned in a form recognized by
     * Vuetify's data-table.
     */
    getCalendarHeader: function(sites, start, ndays) {
        var days = this.daysRange(start, ndays);
        var header = new Array(ndays + 1);
        header[0] = {
            text: "",
            sortable: false,
            value: "name",
            align: "start"
        };
        for (var i = 0; i < days.length; i++) {
            header[i + 1] = {
                month: days[i].month,
                day: days[i].day,
                value: "k-" + i,
                sortable: false,
                align: "center"
            };
        }
        return header;
    },
    getCalendarItems: function(sites, start, ndays) {
        var days = this.daysRange(start, ndays);

        var items = new Array(sites.length);

        for (var i = 0; i < sites.length; i++) {
            var site = sites[i];

            var domain = this.getDomain(site.site_id);
            var row = {
                site_id: site.site_id,
                domain: domain,
                groupIndex: this.groupIndex(domain),
                cols: new Array(ndays)
            };
            items[i] = row;

            for (var j = 0; j < days.length; j++) {
                var day = days[j];
                var branches = this.branchSort(this.getDayData(site, day).branches);
                var branchR = new Array(branches.length);
                row.cols[j] = branchR;
                for (var k = 0; k < branches.length; k++) {
                    branchR[k] = {
                        key: new String(day.day),
                        state: badness(branches[k]),
                        class: this.calendarBubbleClass(branches[k]),
                        style: this.calendarBubbleStyle(branches[k]),
                        name: branches[k].name
                    };
                }
            }
        }
        return items;
    },
    /**
     * Returns the header for the simplified tests table. The header is returned in a form
     * recognized by Vuetify's data-table.
     */
    getTestsTableHeader: function(sites, tests) {
        var c = CUSTOMIZATION;

        var header = new Array(c.testsTable.tests.length + 1);

        header[0] = {
            text: "",
            sortable: false,
            value: "name",
            align: "start"
        };
        header[1] = {
            text: c.testsTable.suiteName,
            sortable: false,
            value: "suite",
            align: "center"
        };

        for (var i = 0; i < c.testsTable.testNames.length; i++) {
            header[i + 2] = {
                text: c.testsTable.testNames[i],
                sortable: false,
                value: c.testsTable.tests[i],
                align: "center"
            };
        }

        return header;
    },
    getTestsTableItems: function(sites, tests) {
        var c = CUSTOMIZATION;

        var rows = new Array(sites.length);
        var now = moment().utc();
        /* The results in sites are not exactly specific on the time when the tests ran, so
         * cap it at two days */
        var suiteThreshold = now.subtract(2, "days");

        for (var ri = 0; ri < rows.length; ri++) {
            var site = sites[ri];
            var cols = new Array(c.testsTable.tests.length + 1);
            var domain = this.getDomain(site.site_id);
            var row = {
                site_id: site.site_id,
                domain: domain,
                groupIndex: this.groupIndex(domain),
                cols: cols
            };
            rows[ri] = row;

            // last month when we saw a test result
            var lastMonth = Object.keys(site.months).slice(-1).pop();
            var lastDay = Object.keys(site.months[lastMonth]).slice(-1).pop();

            var lastTime = moment().utc();
            // months in moment.js are zero-based for some reason
            lastTime.month(lastMonth - 1).date(lastDay);

            var state = SiteState.NoResults;

            // the last day migth not have tests yet, so also try the day before
            lastTime.add(1, "days");
            for (var d = 0; d < 2; d++) {
                lastTime.subtract(1, "days");
                if (lastTime.isBefore(suiteThreshold)) {
                    // last reported tests are more than 1-2 days old
                    state = SiteState.NoResults;
                    break;
                }
                else {
                    var month = (lastTime.month() + 1).toString();
                    var day = lastTime.date().toString();
                    var mainBranch = site.months[month][day].branches.filter(
                        b => b.name == "main" || b.name == "master").pop();
                    if (mainBranch) {
                        state = badness(mainBranch);
                        break;
                    }
                    else {
                        // loop
                    }
                }
             }

            // this is different in the closure
            var siteStateCSSClass = this.siteStateCSSClass;

            var mkresult= function(state) {
                return {
                    key: "suite",
                    state: state,
                    class: siteStateCSSClass(state) + " bubble-large",
                    style: "",
                    name: "main"
                };
            };
            cols[0] = [mkresult(state)];

            if (site.site_id in tests) {
                var siteTests = tests[site.site_id];

                // and then the tests
                for (var ci = 0; ci < c.testsTable.tests.length; ci++) {
                    var testKey = c.testsTable.tests[ci];
                    if (testKey in siteTests) {
                        var test = siteTests[testKey];
                        var passed = true;
                        if (testKey in test) {
                            // SDK needs fixing
                            passed = test[testKey]["passed"];
                        }
                        else {
                            // if only there was a nice way of iterating over an array
                            passed = ["setup", "call", "teardown"]
                                .filter(step => step in test)
                                .reduce((p, step) => p && test[step]["passed"], true);
                        }
                        var state = passed ? SiteState.AllPassed : SiteState.MostFailed;
                        cols[ci + 1] = [mkresult(state)];
                    }
                    else {
                        cols[ci + 1] = [mkresult(SiteState.NoResults)];
                    }
                }
            }
            else {
                // nothing from that site, so all tests are empty
                for (var ci = 0; ci < c.testsTable.tests.length; ci++) {
                    cols[ci + 1] = [mkresult(SiteState.NoResults)];
                }
            }
        }

        return rows;
    },
    /**
     * Groups the status on each day/branch of a number of sites (mostly for use in as calendar
     * domain groups) by computing a GroupState based on the SiteState values for each site in
     * a particular day and branch.
     */
    tableSiteGroups: function(sites) {
        if (sites.length < 2) {
            return [];
        }
        var ncols = sites[0].cols.length;

        var group = new Array(ncols);

        for (var j = 0; j < ncols; j++) {
            group[j] = {
                branches: {},
                orderedBranches: []
            };
        }

        for (var i = 0; i < sites.length; i++) {
            var site = sites[i];
            if (site.cols.length != ncols) {
                throw new Error("Site " + site.site_id + " has an incorrect number of columns (" + site.cols.length + "). Expected " + ncols);
            }
            for (var j = 0; j < ncols; j++) {
                var branches = site.cols[j];
                for (var k = 0; k < branches.length; k++) {
                    var branch = branches[k];
                    if (!(branch.name in group[j].branches)) {
                        group[j].branches[branch.name] = {
                            missingCount: 0,
                            failedCount: 0,
                            completedCount: 0,
                            // for troubleshooting
                            col: j,
                            name: branch.name
                        }
                        group[j].orderedBranches.push(group[j].branches[branch.name]);
                    }
                    var branchData = group[j].branches[branch.name];

                    switch (branch.state) {
                        case SiteState.AllPassed:
                            branchData.completedCount++;
                            break;
                        case SiteState.SomeFailed:
                        case SiteState.MostFailed:
                        case SiteState.RunFailed:
                            branchData.failedCount++;
                            break;
                        case SiteState.NoResults:
                            branchData.missingCount++;
                            break;
                        default:
                            throw new Error("State not handled: " + state);
                    }
                }
            }
        }

        for (var i = 0; i < ncols; i++) {
            var col = group[i];
            for (var k = 0; k < col.orderedBranches.length; k++) {
                var branch = col.orderedBranches[k];
                if (branch.missingCount > 0) {
                    if (branch.failedCount > 0) {
                        branch.state = GroupState.MissingAndFailed;
                    }
                    else if (branch.completedCount > 0) {
                        branch.state = GroupState.MissingAndPassed;
                    }
                    else {
                        branch.state = GroupState.NoResults;
                    }
                }
                else {
                    if (branch.failedCount > 0) {
                        branch.state = GroupState.SomeFailed;
                    }
                    else {
                        branch.state = GroupState.AllPassed;
                    }
                }

                branch.class = this.groupBubbleClass(branch.state, branch.name);
            }
        }

        return group.map(g => g.orderedBranches);
    },
    /**
     * Sets a flag in each of the items if they are part of a group
     */
    setInGroup: function(items) {
        if (items.length > 1) {
            for (let i = 0; i < items.length; i++) {
                items[i].inGroup = true;
            }
        }
        else {
            items[0].inGroup = false;
        }
    },
    calendarBubbleClass: function(branchData) {
        if (branchData == null || (branchData.completed_count == 0 && branchData.failed_count == 0)) {
            return "state-unknown " + this.branchCSSClass(branchData.name);
        }
        else {
            return this.siteStateCSSClass(badness(branchData)) + " " + this.branchCSSClass(branchData.name);
        }
    },
    calendarBubbleStyle: function(branchData) {
        return globalMethods.calendarBubbleStyleObj(branchData);
    },
    calendarBubbleStyleObj: function(branchData) {
        var color;
        if (branchData != null) {
            var completed = branchData.completed_count;
            var failed = branchData.failed_count;

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
    groupBubbleClass: function(groupState, branchName) {
        return this.groupStateCSSClass(groupState) + " " + this.branchCSSClass(branchName);
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
