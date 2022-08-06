var VC = VC || {};

VC.RowAccordian = Vue.component("row-accordian", {
    props: ['rows'],
    data: function () {

        return {
            show: 0
            }
    },
    template: '<table>' +
        '</table>',
    mounted: function( event ) {
    },
    methods: {
        toggle: function( event ) {

        }
    }
});
