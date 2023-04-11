CUSTOMIZATION = {
    projectName: "SDK"
};

var CONF = {
    backendURL: "",
    STR: {
        "dashboardTitle": "ExaWorks SDK Testing Dashboard"
    },
    "curated_sites": {
        xaxis: [
            "Tests Suites",
            "Flux",
            "Parsl",
            "Parsl-flux",
            "RP",
            "Swift-t"
        ],
        xaxisTests: [
            "flux",
            "parsl",
            "parsl-flux",
            "rp",
            "swift-t"
        ],
        yaxis: [
            {
                logo_src: "",
                logo_name: "Lawrence Livermore National Lab",
                machines: {
                    "llnl-lassen": {
                        scheduler: "SLURM"
                    },
                    "llnl-quartz": {
                        scheduler: "SLURM"
                    },
                    "llnl-ruby": {
                        scheduler: "SLURM"
                    }
                }
            },
            {
                logo_src: "",
                logo_name: "GitHub Actions",
                machines: {
                    "Github Actions": {
                        scheduler: "none"
                    }
                }
            }
        ]
    }
};

