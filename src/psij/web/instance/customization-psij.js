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
            "Tests",
            "Quickstart example",
            "Simple Ensemble"
        ],
        xaxisTests: [
            "test_parallel_jobs[local:mpirun]",
            "test_simple_job[slurm:single]",
            "test_simple_job[slurm:multiple]"
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
                        scheduler: "SLURM"
                    },
                    "jupiter.hidden.uoregon.edu": {
                        scheduler: "SLURM"
                    },
                    "reptar.hidden.uoregon.edu": {
                        scheduler: "SLURM"
                    },
                    "saturn.hidden.uoregon.edu": {
                        scheduler: "SLURM"
                    },
                    "orthus.hidden.uoregon.edu": {
                        scheduler: "SLURM"
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

