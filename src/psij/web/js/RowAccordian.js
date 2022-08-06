var VC = VC || {};

VC.RowAccordian = Vue.component("row-accordian", {
    props: [
        'logo_name',
        'machines',
        'logo_results',
        'machine_row_results'
    ],
    data: function () {

        return {
            open: 1
            }
    },
    template: '<table>' +
        '</table>',
    mounted: function( event ) {
    },
    methods: {
        toggle: function( event ) {

            this.open = this.open ? 0 : 1;
        }
    }
});
