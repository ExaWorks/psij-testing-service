CUSTOMIZATION = {
    projectName: "PSI/J",
    title: "PSI/J Testing Dashboard",
    // If not specified, relative links are used, so it works on any domain
    backendURL: "",
    reCaptchaSiteKey: "",
    testsTable: {
        tests: [
            "test_simple_job[local:single]",
            "test_parallel_jobs[local:single]"
        ],
        testNames: [
            "Basic test",
            "Parallel jobs"
        ],
        suiteName: "Test suite"
    }
};

