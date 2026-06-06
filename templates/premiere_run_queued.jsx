#target premiere
/**
 * Installed by: python main.py install-premiere
 * When Premiere is already open, workflow writes queue.txt and you run this once:
 *   File → Scripts → Run Automated Workflow
 */
(function () {
    var queueDir = Folder.appData.fsName + "/Automated-script";
    var queueFile = new File(queueDir + "/queue.txt");
    if (!queueFile.exists) {
        alert(
            "No automation is queued.\n\n" +
            "Run in PowerShell:\n" +
            "  python main.py workflow --number 003"
        );
        return;
    }
    queueFile.open("r");
    var targetPath = queueFile.read().replace(/^\s+|\s+$/g, "");
    queueFile.close();
    queueFile.remove();

    if (!targetPath) {
        alert("Queue file was empty. Run workflow again.");
        return;
    }

    var script = new File(targetPath);
    if (!script.exists) {
        alert("Automation script not found:\n" + script.fsName);
        return;
    }

    $.evalFile(script);
})();
