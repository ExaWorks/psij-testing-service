var PS = PS || {};

PS.CodeCoverageView = function() {

    var file_idx_ = 0;
    var line_count_ = 1;

    var STUB_FROM_BE = {
        files: [
            {
                name: "service.py",
                coverage: [{
                    lines: [
                        "import argparse",
                        "import datetime",
                        "import json",
                        "import logging",
                        "import sys",
                        "from pathlib import Path",
                        "from typing import Optional, Dict, cast"
                    ],
                    status: "green"
                },
                    {
                        lines: [
                        "from mongoengine import Document, StringField, DateTimeField, connect, DictField, BooleanField, \\",
                        "    IntField",
                        "",
                        "",
                        "CODE_DB_VERSION = 2",
                        "",
                        "",
                        "def upgrade_0_to_1() -> None:",
                        "    pass",
                        "",
                        ""
                    ],
                    status: "white"
                },
                    {
                    lines: [
                                                "def upgrade_1_to_2() -> None:",
                        "    RunEnv.objects().update(skipped_count=0)",
                        "    Site.create_index(['last_seen'])",
                        "    RunEnv.create_index(['site_id', 'run_id'])",
                        "    RunEnv.create_index(['site_id', 'run_id', 'branch'])",
                        "    Test.create_index(['site_id', 'run_id', 'branch'])",
                        "",
                        "",
                        "DB_UPGRADES = {",
                        "    0: upgrade_0_to_1,",
                        "    1: upgrade_1_to_2",
                        "}",
                        "",
                        "class Version(Document):",
                        "    version = IntField(required=True)",
                        "",
                        "",
                        "class Site(Document):",
                        "    site_id = StringField(required=True, unique=True)",
                        "    key = StringField(required=True)",
                        "    last_seen = DateTimeField(required=True)",
                        "    crt_maintainer_email = StringField()",
                        "    ip = StringField()",
                        "",
                        "",
                        "class Test(Document):",
                        "    site_id = StringField(required=True)",
                        "    test_start_time = DateTimeField(required=True)",
                        "    test_end_time = DateTimeField(required=True)",
                        "    stdout = StringField()",
                        "    stderr = StringField()",
                        "    log = StringField()",
                        "    module = StringField()",
                        "    cls = StringField()",
                        "    function = StringField()",
                        "    test_name = StringField()",
                        "    results = DictField()"
                    ],
                    status: "red"
                }]
            },
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
            ht += "<div class='file_line' file_index='"+  x + "'>" + fileObj.name + '</div>';
        }

        $('.select-page').html( ht );

        $('.select-page .file_line').unbind('click').bind('click', file_selected_ );
    };


    var file_selected_ = function() {

        file_idx_ = $(this).attr('file_index');
        init_();
    };

    var get_coverage_ = function() {

        var context = 'http://localhost:9909/coverage';
        //PS.getURL('coverage');

        $.get(context, {}, function(data) {

            console.dir( data );
        });
    };


    var init_ = function() {

        line_count_ = 0;

        make_left_side_();
        make_right_side_();

        get_coverage_();
    };

    $(document).ready( init_ );

    return {
        get_coverage: get_coverage_
    };
}();