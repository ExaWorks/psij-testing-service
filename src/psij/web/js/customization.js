CUSTOMIZATION = {
    projectName: "PSI/J"
}

var CONF = {
    STR: {
        "dashboardTitle": "Exascale dashboard testing service",
        "introBlurb": "The dashboard testing service shows you the status of various sites in the calendar view by date and machine without curation.",
        "bottomBlurb": "The curated sites tab will eventually show labs on the left which are expandable to show the machines of each lab on the y axis.  Meanwhile, the X axis will show you test cases like PSI/J and PSI/J Parcel, etc."
    },
    "curated_sites": {
        xaxis: [
            "PSI/J",
            "PSI/J + Parsl",
            "PSI/J + Swift",
            "RADICAL-Pilot"
        ],
        yaxis: [
            {
                logo_src: "",
                logo_name: "Lawrence Livermore National Lab",
                machines: [
                    "Livermore North",
                    "Livermore South",
                    "Livermore 4th st."
                ]
            },
            {
                logo_src: "",
                logo_name: "Argonne",
                machines: [
                    "Arg 1",
                    "Arg 2"
                ]
            },
            {
                logo_src: "",
                logo_name: "Brookhaven National Lab",
                machines: [
                    "Brook River",
                    "Brook Sim"
                ]
            },
            {
                logo_src: "",
                logo_name: "Oakride National Lab",
                machines: [
                    "Oak 1",
                    "Oak 2",
                    "Oak 3",
                    "Oak 4"
                ]
            }
        ]
    }
};

