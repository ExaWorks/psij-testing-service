CUSTOMIZATION = {
    projectName: "PSI/J"
};

var CONF = {
    backendURL: "https://psij.testing.exaworks.org/",
    STR: {
        "dashboardTitle": "Exascale dashboard testing service"
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
                        scheduler: "SLURM"
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
                logo_name: "Oakridge National Lab",
                machines: {
                }
            }
        ]
    }
};

