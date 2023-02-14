var VC = VC || {};

VC.goHere = function(ev) {

    var x = $(event.target);
    var site_id = x.html();

    window.location="site.html?site_id=" + site_id;
};


VC.RowAccordion = Vue.component("row-accordion", {
    props: [
        'show_scheduler',
        'yaxe_prop' //  one yaxis property: logo_name, logo source and machines list.
    ],
    data: function () {

        return {
            open: 0
            }
    },
    template: '<table class="RowAccordion">' +
            '<tr>' +
        '<td v-on:click="toggle( $event )" class="logo_name">' +
        '<div v-if="this.open == 1" class="ArrowRight"></div>' +
        '<div v-if="this.open == 0" class="ArrowDown"></div>' +
        '{{ this.yaxe_prop.logo_name }}</td>' +
        '<td class="scheduler-cell" v-if="show_scheduler"></td>' +
        '<td class="status-cell" v-for="summaryState in yaxe_prop.horizontalSummary">' +
        '<div :class=\'"calendar-bubble " + summaryState + " bubble-large"\'></div>' +
        '</td>'+
            '</tr> \
            <tr :class=\'open == 0 ? "rowIsOpen" : "rowIsClosed"\' v-for="machineObj in yaxe_prop.machinesFromModel">\
            <td class="machineLink highlightable" :onclick=\'"event.stopPropagation(); VC.goHere();" \'>{{ machineObj.machine }}</td>' +
            '<td v-if="show_scheduler" class="schedulerCol">{{ machineObj.schedulerShow }}</td>' +
        '<td class="status-cell" v-for="state in machineObj.states">' +
            '<div :class=\'"calendar-bubble " + state.mainState + " bubble-large"\'></div>' +
            '<div class="container-for-mini-branches">' +
            '<div class="calendar-bubble" v-for="branch in state.branches" ' +
            '        :class="branch.calendarBubbleClass">' +
            '        &nbsp;' +
            '</div>' +
            '</div>' +
        '</td>'+
            '</tr>' +
        '</table>',
    mounted: function( event ) {

        PS.showOrHideBranchBubbles();
    
    },
    methods: {
        toggle: function( event ) {

            this.open = this.open ? 0 : 1;
            console.log( this.open );
        },
        nice_bubble: function( state ) {
            console.dir(state);
            return '<div class="calendar-bubble state-good, bubble-large" style="background-color: rgb(106, 255, 77);">\n' +
                '                            &nbsp;\n' +
                '                        </div>';
        }
    }
});
