CUSTOMIZATION = {
    projectName: "PSI/J"
};

var CONF = {
    backendURL: "https://testing.psij.io/",
    STR: {
        "dashboardTitle": "PSI/J Testing Dashboard"
    },
    "curated_sites": {
        xaxis: [
            "Tests Suite",
            "Basic test",
            "Parallel jobs"
        ],
        xaxisTests: [
            "test_simple_job[local:single]",
            "test_parallel_jobs[local:single]"
        ],
        yaxis: [
            {
                logo_src: "",
                logo_name: "University of Oregon",
                machines: {
                    "echo.test": {
                        scheduler: ""
                    },
                    "axis1.hidden.uoregon.edu": {
                        scheduler: "SLURM"
                    },
                    "illyad.hidden.uoregon.edu": {
                        scheduler: ""
                    },
                    "jupiter.hidden.uoregon.edu": {
                        scheduler: ""
                    },
                    "reptar.hidden.uoregon.edu": {
                        scheduler: ""
                    },
                    "saturn.hidden.uoregon.edu": {
                        scheduler: ""
                    },
                    "orthus.hidden.uoregon.edu": {
                        scheduler: ""
                    }
                }
            },
            {
                logo_src: "",
                logo_name: "Lawrence Livermore National Lab",
                machines: {
                    "doc.llnl.gov": {
                        scheduler: ""
                    },
                    "quartz.llnl.gov": {
                        scheduler: ""
                    },
                    "lassen.llnl.gov": {
                        scheduler: ""
                    },
                    "ruby.llnl.gov": {
                        scheduler: ""
                    }
                }
            },
            {
                logo_src: "",
                logo_name: "Nersc National Lab",
                machines: {
                    "cori08.nersc.gov": {
                        scheduler: "SLURM"
                    },
                    "perlmutter.nersc": {
                        schedulor: "SLURM"
                    }
                }
            },
            {
                logo_src: "",
                logo_name: "ALF",
                machines: {
                    "polaris.alcf.anl.gov":{scheduler: ""},
                    "theta.alcf.anl.gov":{scheduler: ""},
                    "bebop.lcrc.anl.gov": {
                        scheduler: ""
                    }
                }
            }
        ]
    }
};

