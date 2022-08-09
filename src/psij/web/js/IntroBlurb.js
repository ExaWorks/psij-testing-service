var VC = VC || {};

VC.IntroBlurb = Vue.component("intro-blurb", {
    data: function () {

        return {
            show: 0
            }
    },
    template: '<div v-if="this.show == 1" ref="myRef" class="IntroBlurb" v-on:click="close( $event )">' +
        '<div class="main_slot"><slot></slot></div>' +
        '<div class="CloseMe">X</div>' +
        '</div>',
    mounted: function( event ) {
        console.log('mounted');
        var content = this.$slots.default[0].text;
        console.dir( content );

        if( sqs.IntroBlurb && sqs.IntroBlurb[ content ] ) {
            //  hide
            this.show = 0;
        } else {
            this.show = 1;
        }
    },
    methods: {
        close: function( event ) {

            var ihtml = this.$el.firstChild.innerHTML;
            console.log(ihtml);

            sqs.IntroBlurb = sqs.IntroBlurb || {};
            sqs.IntroBlurb[ ihtml ] = 1;
            sq.save();

            this.show = 0;
        }
    }
});
