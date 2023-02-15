var PS = PS || {};
/*
    This builds the Data model for the curated sites view.
 */
PS.SitesModel = function() {

    var callback_;

    var getModel_ = function( callback ) {

        callback_ = callback;
        getLatestResultForTestOnAllSites_();
    };


    var makeModel_ = function() {

        var curSite = makeModelInstance_( CONF.curated_sites );

        callback_( curSite );
    };


    var makeModelInstance_ = function( cur_site ) {

        var curSite = $.extend({}, cur_site );

        for( var yIndex=0; yIndex < curSite.yaxis.length; yIndex++ ) {

            var machinesInAccordion = [];

            curSite.yaxis[yIndex].horizontalSummary = makeGoodStatesArray_(curSite.xaxis.length);

            loadMachines_( curSite, machinesInAccordion, yIndex);

            curSite.yaxis[yIndex].machinesFromModel = machinesInAccordion;


        }

        return curSite;
    };


    var makeGoodStatesArray_ = function( entryCount ) {

        var x = new Array(entryCount).fill(PS.STATES.GOOD);
        console.log(x);
        return x;
    };

    var getMainBranch_ = function( branches ) {

        var branchToSearchFor = location.href.indexOf("/sdk.") > -1 ? "master" : "main";

        for( var i=0; i < branches.length; i++ ) {

            var branch = branches[i];
            if( branch.name === branchToSearchFor) {
                    return branch;
            }
        }

        return null;
    };


    var loadMachines_ = function( curSite, machinesInAccordion, yIndex ) {

        var yobj = curSite.yaxis[yIndex];

        for( var siteId in yobj.machines ) {

            var machinesObj = yobj.machines[siteId];
            var site = getSiteBySiteId_(siteId);

            if (site) {

                var keys = Object.keys( site.months );
                var lastKeyIdx = keys.length - 1;
                var lastMon = keys[ lastKeyIdx ];

                var days = site.months[lastMon];
                var daysKeys = Object.keys( days );
                var lastDayKeyIdx = daysKeys.length - 1;
                var lastDay = daysKeys[ lastDayKeyIdx ];

                var sobj_outer = site.months[lastMon][lastDay];
                var sobj = getMainBranch_( sobj_outer.branches );

                if( sobj === null) {
                    //  case where there are no branches or no main branch.
                    sobj = {
                        completed_count:0,
                        failed_count:0,
                        name: 'none'
                    }
                }

                var state = globalMethods.badnessClass(sobj);
                var states = [state];

                for( var cIndex = 0; cIndex < 6; cIndex++ ) {

                    var s = getMachineStateByTestingColumn_(siteId, cIndex );

                    if( s !== PS.STATES.GOOD && s !== "" && curSite.xaxis.length > (cIndex+1) ) {
                        curSite.yaxis[yIndex].horizontalSummary[cIndex+1] = PS.STATES.REALLY_BAD;
                    }

                    if (curSite.xaxis.length > (cIndex+1)) {
                        states.push(s);
                    }
                }

                var objStates = [];

                for( var y=0; y < states.length; y++ ) {
                    objStates.push({
                       mainState: states[y],
                       branches: []
                    });
                }

                machinesInAccordion.push({
                    machine: siteId,
                    schedulerShow: machinesObj.scheduler,
                    states: objStates
                });
            }
        }
    };


    /*
     *  curated sites:
     *      columnIndex - 0 is the first column, "Test Suite",
     *          1 is Tests, etc.
     */
    var getMachineStateByTestingColumn_ = function( siteId, columnIndex) {

        var xTests = CONF.curated_sites.xaxisTests;
        var testName = xTests[columnIndex];

        var resultSetupAndCall = resultsBySiteIdAndCol_[ siteId ][ testName ];

        var bl = getStatus_(resultSetupAndCall, testName);
        return bl;
    };


    var getMachineArray_ = function() {

        var yaxis = CONF.curated_sites.yaxis;
        var machine_arr = [];

        for( var x in yaxis ) {

            var lm_obj = yaxis[x];
            var machineKeys = Object.keys(lm_obj.machines);
            machine_arr = machine_arr.concat( machineKeys )
        }

        return machine_arr;
    };


    var getLatestResultForTestOnAllSites_ = function() {

        var t_arr = CONF.curated_sites.xaxisTests;
        var js = JSON.stringify( t_arr );
        var path = "tests";
        var ma = getMachineArray_();
        var params = "sites_to_get=" + JSON.stringify( ma ) +
                "&tests_to_match=" + js;

        var url = PS.getURL(path);

        $.get(url, params, handleTests_);
    };


    var resultsBySiteIdAndCol_ = {};

    var handleTests_ = function(results) {

        resultsBySiteIdAndCol_ = results;

        makeModel_();
        callback_();
    };


    var handleColumn_ = function( zCol, testsBySites ) {

        var xTests = CONF.curated_sites.xaxisTests;
        var testName = xTests[zCol];

        for( var siteId in testsBySites ) {

            var result = getResult_( testsBySites[siteId], testName );
            console.log('siteId: ' + siteId);
            var boolRes = getStatus_( result );

            resultsBySiteIdAndCol_[ siteId ] = resultsBySiteIdAndCol_[ siteId ] || [];
            resultsBySiteIdAndCol_[ siteId ][ zCol ] = boolRes;

            //console.log( siteId );
            //console.dir( result );
        }
    };


    var getStatus_ = function( result, testName ) {

        //  SDK page send back results in a slightly different format.
        if( result && result[testName] ) {

            return result[testName].passed === true ? PS.STATES.GOOD : PS.STATES.REALLY_BAD;
        }

        //  PSIJ
        if( result === undefined ) {
            return PS.STATES.EMPTY;
        }

        if( result && result.call && result.call.passed &&
            result.setup && result.setup.passed ) {

            return PS.STATES.GOOD;
        }

        return PS.STATES.REALLY_BAD;
    };


    var getResult_ = function( allTestsForSite, testName ) {

        for( var i=0; i < allTestsForSite.length; i++ ) {

            var test = allTestsForSite[i];

            if( test.test_name === testName ) {
                console.log('branch: ' + test.branch);
                return test.results;
            }
        }

        return false;
    };



    var getSiteBySiteId_ = function( siteId ) {

        for( var y=0; y < PS.sites.length; y++ ) {

            var site = PS.sites[y];

            if( siteId === site.site_id ) {
                return site;
            }
        }

        return null;
    };


    var calendarBubbleClass_ = function(d) {

        var size = function(name) {
            return name == "main" || name == "master" ? "bubble-large" : "bubble-small";
        };

        var bc = globalMethods.badnessClass( d );

        if (d == null || (d.completed_count == 0 && d.failed_count == 0)) {
            return "state-unknown ";
        }
        else {
            return globalMethods.badnessClass(d) + " " + size(d.name);
        }
    };

    var getBranchesForSmallBubbles_ = function( branches ) {

       var br = [];

       for( var x=0; x < branches.length; x++ ) {

           var branch = branches[x];
           var bc = calendarBubbleClass_( branch );
           var bs = globalMethods.calendarBubbleStyleObj( branch );

           if( branch.name !== "main" && branch.name !== "master") {
               br.push({
                   calendarBubbleClass: bc,
                   calendarBubbleStyle: bs
               });
           }
       }

       return br;
    };

    return {
        getBranchesForSmallBubbles: getBranchesForSmallBubbles_,
        getMainBranch: getMainBranch_,
        getLatestResultForTestOnAllSites: getLatestResultForTestOnAllSites_,
        getModel: getModel_
    }
}();