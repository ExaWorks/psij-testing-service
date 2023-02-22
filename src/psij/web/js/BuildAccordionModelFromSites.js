/*
    This builds the DataModel for the Calendar View.
    It preps the Data for consumption.
 */
PS.BuildAccordionModelFromSites = function() {

    var get_states_ = function( months ) {

        var sts = [];
        var objStates = [];

        for( var month in months ) {

            var days = months[month];

            for( var day in days ) {

                var res = days[day];

                var sobj = PS.SitesModel.getMainBranch( res.branches );

                if( sobj === null) {
                    //  case where there are no branches or no main branch.
                    sobj = {
                        completed_count:0,
                        failed_count:0,
                        name: 'none'
                    }
                }

                var bc = globalMethods.badnessClass(sobj);
                sts.push(bc);

                var branches = PS.SitesModel.getBranchesForSmallBubbles( res.branches );

                objStates.push({
                    mainState: bc,
                    branches: branches
                });
            }
        }

        return objStates;
    };


    var get_ = function( accordionModelRef ) {

        //  Accordion Model.
        var am = [];
        var machObjs = {};

        for( var x=0; x < PS.sites.length; x++ ) {

            var site = PS.sites[x];
            var siteId = globalMethods.getDomain(site.site_id);

            machObjs[siteId] = machObjs[siteId] || [];
            machObjs[siteId].push({
                machine: site.site_id,
                states: get_states_(site.months ) //["state-good","state-good","state-really-bad","state-good","state-good","state-bad", "state-good", "state-good"]
            });
        }


        for( var siteId in machObjs ) {

            am.push({
                logo_name: siteId,
                machinesFromModel: machObjs[siteId]
            });
        }

        for( var i=0; i < am.length; i++ ) {
            accordionModelRef[i] = am[i];
        }

        accordionModelRef.splice(am.length);

        /* EXAMPLE STUB:
            return [{
            logo_name: "uregon.edu",
            machinesFromModel: [{
                machine: "axis833334.uregon.edu",
                states: ["state-good","state-good","state-really-bad","state-good","state-good"]
            },
            {
                machine: "axis8690003.uregon.edu",
                states: ["state-good","state-good","state-really-bad","state-good","state-good"]
            },
            {
                machine: "axis2222283.uregon.edu",
                states: ["state-good","state-good","state-really-bad","state-good","state-good"]
            }]
        }];*/
    };

    return {
        get: get_
    }
}();