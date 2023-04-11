var PS = PS || {};

PS.CodeCoverageView = function() {

    var file_idx_ = 0;
    var line_count_ = 1;

    var STUB_FROM_BE = {
        files: [
            {
                name: "__init__.py",
                coverage: [{
                    lines: [
                        "for( var x=0; x < 5; x++) {",
                        "   w=5;",
                        "}"
                    ],
                    status: "green"
                },
                    {
                        lines: [
                            "# comments should be here."
                        ],
                        status: "white"
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
                coverage: [{
                    lines: [
                        "if( code_note == 3 ) {",
                        "}"
                    ],
                    status: "red"
                }]}
        ]
    };


    var make_right_side_ = function() {

        var coverage = STUB_FROM_BE.files[ file_idx_ ].coverage;
        var ht = "";

        for( var x=0; x < coverage.length; x++ ) {

            var covObj = coverage[x];
            var linesHTML = "";
            //covObj.lines.join("<br>");

            for( var j=0; j < covObj.lines.length; j++ ) {
                linesHTML += "<div class='line_count'>" + line_count_ + "</div>" +
                    "<div class='line'>" + covObj.lines[j] + "</div><br>";
                line_count_++;
            }

            ht += '<div class="' + covObj.status + '">' + linesHTML + '</div>';
        }

        $('.right-side').html( ht );
    };


    var make_left_side_ = function() {

        var ht = "<div class='files_header'>Files</div>";
        var files = STUB_FROM_BE.files;

        for( var x=0; x < files.length; x++ ) {

            var fileObj = files[x];
            ht += "<div class='file_line' file_index='" + x + "'>" + fileObj.name + '</div>';
        }

        $('.select-page').html( ht );

        $('.select-page .file_line').unbind('click').bind('click', file_selected_ );
    };


    var file_selected_ = function() {

        file_idx_ = $(this).attr('file_index');
        init_();
    };

    var init_ = function() {

        line_count_ = 0;
        make_left_side_();
        make_right_side_();
    };

    $(document).ready( init_ );

    return {};
}();