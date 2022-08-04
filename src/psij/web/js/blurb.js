var VC = VC || {};

VC.IntroBlurb = Vue.component("intro-blurb", {
    data: function () {

        return {
            }
    },
    template: '<div class="IntroBlurb">' +
        '<slot></slot>' +
        '</div>',
    methods: {}
});
