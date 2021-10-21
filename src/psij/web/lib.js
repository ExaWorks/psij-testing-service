var badness = function(obj) {
    if (obj['failed_count'] > 0) {
        if (obj['completed_count'] < obj['failed_count']) {
            return 2;
        }
        else {
            return 1;
        }
    }
    else {
        return 0;
    }
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
    return null;
}

var ansi_up = new AnsiUp();
ansi_up.use_classes = true;


var globalMethods = {
    sort: function(key, lst) {
        console.log(lst);
        if (!lst) {
            return lst;
        }
        return lst.slice().sort((a, b) => {
            var av = a[key];
            var bv = b[key];
            return av > bv ? 1 : (av == bv) ? 0 : -1;
        });
    },
    limit: function(array, n) {
        if (array.length > n) {
            return array.slice(0, n);
        }
        else {
            return array;
        }
    },
    badnessClass: function(obj) {
        switch(badness(obj)) {
            case 0:
                return "state-good";
            case 1:
                return "state-somewhat-bad";
            case 2:
                return "state-really-bad";
        }
    },
    badnessSort: function(lst) {
        return lst.slice().sort((a, b) => {
            return badness(a) - badness(b);
        });
    },
    navigate: function(loc) {
        console.log(loc);
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
            return 0;
        }
        var passed = true;
        for (var k in results) {
            passed &= results[k].passed;
        }

        if (passed) {
            return 1;
        }
        else {
            return 2;
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
                    return '<div class="listing listing-text">' + value + '</div>';
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
        var crt = now.clone();
        crt.addDays(-ndays + 1);
        var change = false;
        for (var i = 0; i < ndays; i++) {
            var day = crt.getDate();
            var entry = new Object();
            days.push(entry);
            entry.day = day;
            entry.monthChange = false;
            entry.cls = "month-none";
            entry.month_num = crt.getMonth() + 1;
            if (day == 1) {
                entry.monthChange = true;
                if (i > 0) {
                    crt.addDays(-1);
                    days[i - 1].month = crt.toString("MMMM");
                    crt.addDays(1);
                }
                days[i].month = crt.toString("MMMM");
                change = true;
            }
            crt.addDays(1);
        }
        if (!change) {
            days[0].month = crt.toString("MMMM");
        }
        return days;
    },
    calendarTileClass: function(site, day) {
        var d = getDayData(site, day);
        if (d == null || (d.completed_count == 0 && d.failed_count == 0)) {
            return "state-unknown";
        }
        else {
            return this.badnessClass(d);
        }
    },
    calendarTileStyle: function(site, day) {
        var d = getDayData(site, day);
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
    breadcrumbs: function() {
        var b = [{text: "PSI/J Tests", href: "summary.html"}];
        var level = 0;
        if (window.location.pathname.startsWith("/site.html")) {
            level = 1;
        }
        if (window.location.pathname.startsWith("/run.html")) {
            level = 2;
        }
        if (level >= 1) {
            b.push({text: "Site " + this.site.site_id})
        }
        if (level >= 2) {
            b.push({text: "Run " + this.shortenId(this.run.run_id)})
        }
        return b;
    }
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