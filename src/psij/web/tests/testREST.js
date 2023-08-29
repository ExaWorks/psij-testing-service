//  For now, Used for Testing
var getLatestResultForTestOnAllSites = function() {

    var machinesToGet = ["axis1.hidden.uoregon.edu","illyad.hidden.uoregon.edu","jupiter.hidden.uoregon.edu","reptar.hidden.uoregon.edu","saturn.hidden.uoregon.edu","orthus.hidden.uoregon.edu","doesnotexistTEST.edu","doc.llnl.gov","cori08.nersc.gov","perlmutter.nersc","doesNOTexistTEST.edu2"];

    var testsToMatch = ['test_parallel_jobs[batch-test:mpirun]','test_cancel[local:single]', 'test_failing_job[batch-test:mpirun]'];
    //  getLatestResultForTestOnAllSites
    var context = "tests";
    var params = "sites_to_get=" + JSON.stringify( machinesToGet ) + '&' +
                    "tests_to_match=" + JSON.stringify(testsToMatch)

    $.get(context, params, function(data) {
        console.dir(data);
        //var date = data['axis1.hidden.uoregon.edu']['test_attach[batch-test:mpirun']['test_start_time'];
        //console.log('date: ' + date);
    });
};