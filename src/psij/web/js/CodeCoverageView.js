var PS = PS || {};

PS.CodeCoverageView = function() {

    var STUB_FROM_BE = {
        files: [
            {
                name: "__init__.py",
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
            },
            {
                name: "descriptor.py",
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
                ]},
            {name: "job.py",
                coverage: []}
        ]
    };


    var make_right_side_ = function() {

        var coverage = STUB_FROM_BE.files[0].coverage;
        var ht = "";

        for( var x=0; x < coverage.length; x++ ) {

            var covObj = coverage[x];
            var linesHTML = covObj.lines.join("<br>");
            ht += '<div class="' + covObj.status + '">' + linesHTML + '</div>';
        }

        $('.right-side').append( ht );
    };

    var make_left_side_ = function() {

        var ht = "";
        var files = STUB_FROM_BE.files;

        for( var x=0; x < files.length; x++ ) {

            var fileObj = files[x];
            ht += "<div class='file_line'>" + fileObj.name + '</div>';
        }

        $('.select-page').append( ht );
    };


    var init_ = function() {

        make_left_side_();
        make_right_side_();
    };

    $(document).ready( init_ );

    return {};
}();