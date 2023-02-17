
var setViewMode = function (viewMode) {

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

    if( viewMode === 'calendar' ) {
        setTimeout( PS.bindRowOpenClose, 0 );
    }

    if( viewMode === 'home' ) {
        PS.SitesModel.getLatestResultForTestOnAllSites();
    }
};


PS.SummaryModel = function() {

    var set = function(dst, src) {
        dst.length = 0;
        for (var i = 0; i < src.length; i++) {
            dst.push(src[i]);
        }
    };

    var updateSummary = function() {

        var context = PS.getURL('summary');
        var inact = localStorage.getItem('inactiveTimeout');
        inact = inact ? inact : 10;

        var obj = {
            inactiveTimeout: inact
        };


        $.get(context, obj, function(data) {

            set(PS.sites, data);

            PS.accordionModel = PS.accordionModel || [];
            PS.BuildAccordionModelFromSites.get(PS.accordionModel);

            console.log('after summary get:');
            console.dir(PS.accordionModel);

            PS.makeSites();

            //  Vue wants to rerender this section immediately after this function
            //  That would wipe out showOrHideBranchBubbles.  Give Vue the chance
            //  to do it rerender, then run showOrHideBranchBubbles.
            setTimeout(PS.showOrHideBranchBubbles,0);
        });
    };

    $(document).ready( updateSummary );

    return {
        updateSummary: updateSummary
    }
}();




var siteStatus;

PS.bindRowOpenClose = function() {

    PS.urls = {};
    console.log($('.open_close_arrow').length);

    $('.open_close_arrow').unbind('click').bind('click', function() {

        var parent = $(this).closest('tr');
        var site_el = parent.find('[site_id]');
        var siteIdClicked = site_el.attr('site_id');

        console.log( siteIdClicked );
        $(this).toggleClass('open');

        $('[site_id="' + siteIdClicked + '"][position="otherPosOnc"]').parent().toggle();
    });

    PS.showOrHideBranchBubbles();
};



PS.makeSites = function() {

    var init_ = function( sites_model ) {

        if( !sites_model ) {
            return false;
        }

        PS.BuildAccordionModelFromSites.get(PS.accordionModel);

        siteStatus = new Vue({
            el: "#container",
            components: {
            },
            vuetify: new Vuetify(),
            data: {
                sites: PS.sites,
                accordionModel: PS.accordionModel,
                mode: '',
                now: moment().utc().startOf("day"),
                STR: CONF.STR,
                curated_sites: sites_model,
                settingsDialog: false
            },
            methods: globalMethods,
            computed: {
                inactiveTimeout: makeSetting("inactiveTimeout", PS.SummaryModel.updateSummary),
                showBranchBubbles: makeSetting("showBranchBubbles", PS.SummaryModel.updateSummary, "bool"),
                allBranches: function () {

                    console.log('allBranches:');
                    console.dir(this.sites);

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
                            } else {
                                unique[branch.name] = {...branch};
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
                branchIndexMap: function () {
                    var all = this.allBranches;
                    var map = {};
                    for (var i = 0; i < all.length; i++) {
                        map[all[i].name] = i;
                    }
                    return map;
                }
            }
        });

        setViewMode();
        PS.bindRowOpenClose();
    };



    $(document).ready( PS.bindRowOpenClose );

    if( !PS.already_made_site ) {
        PS.already_made_site = 1;

        PS.SitesModel.getModel( init_ );
    }

    window.reget = function() {
        PS.SitesModel.getModel( init_ );
    };

};