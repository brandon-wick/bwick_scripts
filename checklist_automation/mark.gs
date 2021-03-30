function markAllOk() {
  // Get spreadsheet and sheet
  var ss = app.getActiveSpreadsheet();
  var activeSheet = ss.getActiveSheet();

  // Get status of each platform
  var windowsStatus = activeSheet.getRange(buildChecklist["winCol"] + "2")
  var linuxStatus = activeSheet.getRange(buildChecklist["linCol"] + "2")
  var macStatus = activeSheet.getRange(buildChecklist["macCol"] + "2")

  // Define cell range for each platform's markable area
  var windowsRange = [buildChecklist["winCol"] + buildChecklist["firstMarkableRow"] +":"+ buildChecklist["winCol"] + buildChecklist["lastMarkableRow"]]
  var linuxRange = [buildChecklist["linCol"] + buildChecklist["firstMarkableRow"] +":"+ buildChecklist["linCol"] + buildChecklist["lastMarkableRow"]]
  var macRange = [buildChecklist["macCol"] + buildChecklist["firstMarkableRow"] +":"+ buildChecklist["macCol"] + buildChecklist["lastMarkableRow"]]

  // Mark "OK" for platforms with that have a status of "Incomplete"
  for(i = 0; i < 3; i++) {
    if(windowsStatus.getValue() == "Incomplete") {
      activeSheet.getRangeList(windowsRange).setValue("OK");
      windowsStatus.setValue("All OK");
      } else if(linuxStatus.getValue() == "Incomplete") {
      activeSheet.getRangeList(linuxRange).setValue("OK");
      linuxStatus.setValue("All OK");
      } else if (macStatus.getValue() == "Incomplete") {
      activeSheet.getRangeList(macRange).setValue("OK");
      macStatus.setValue("All OK");}
    }

}
