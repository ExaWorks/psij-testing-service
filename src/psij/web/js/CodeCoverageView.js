PS.CodeCoverageView = function() {

    var STUB_FROM_BE = {
        files: [{name: "__init__.py"}, {name: "descriptor.py"}, {name: "job.py"}],
        coverage: [{
            lines: [
                "# this is a sample code file",
                "# using comments that appear white",
                ""
            ],
            status: "white"
        },
        {
            lines: [
                "var cx=0;",
                "cx = 80;",
                "if( cx == 80 ) { return true; }"
            ],
            status: "green"
        },
            {
            lines: [
                "var not_covered = 2;",
                "if( not_covered ) {",
                "  return 0;",
                "}"
            ],
            status: "red"
        }
        ]
    };



    var init_ = function() {

        var coverage = STUB_FROM_BE.coverage;

        for( var x=0; x < coverage; x++ ) {
            
        }

    };

    $(document).ready( init_ );

    return {};
}();