// get testing schedule
var app = SpreadsheetApp;
var testingSchedule = app.openByUrl("https://docs.google.com/spreadsheets/d/1FcetBnpY1ASeXSFnTdeqvXO7dRIk7AItvHIlbpcL3pM/edit?usp=sharing");

// Insert your product as named in the testing schedule #EDIT THIS
var productRow = rowOfProduct("Product");

// define checklist characteristics for each build #EDIT THIS
var buildChecklist = {"winCol":"E", "linCol":"F", "macCol":"G", "firstMarkableRow":"5", "lastMarkableRow":"15", "percentRow":"16", "borders":["E1:G4", "E5:G7", "E8:G13", "E14:G15"]};

// Range of borders #EDIT THIS
var checklistBorders = ["A1:D4", "A5:D7", "A8:D13", "A14:D15"];

// Upper left portion of checklist #EDIT THIS
var productLabel = {"A":{"1":"Product", "2":"=offset(A1, 0, 4)", "3":"Tester: Gertrude", "4":"Category"},
                    "B":{"1":"Windows Status", "2":'=IF( "Incomplete"=lower(offset(B2,0,3)), concatenate( "Incomplete (", offset( B2,14,3), "%)"),offset(B2,0,3))', "3":"=offset(A3,0,4)", "4":"Feature"},
                    "C":{"1":"Linux Status", "2":'=IF( "Incomplete"=lower(offset(C2,0,3)), concatenate( "Incomplete (", offset( C2,14,3), "%)"),offset(C2,0,3))', "3":"=offset(A3,0,5)", "4":"Details"},
                    "D":{"1":"Darwin Status", "2":'=IF( "Incomplete"=lower(offset(D2,0,3)), concatenate( "Incomplete (", offset( D2,14,3), "%)"),offset(D2,0,3))', "3":"=offset(A3,0,6)", "4":"STU/Squish Tests"}};

// Checklist Section in JSON format. Use a "-" in place of blank/None values #EDIT THIS
var productCheckList = {"Panel 1":[
                          {"Feature":"feature 1", "Details":"-", "Tests":"suite_test"},
                          {"Feature":"feature 2", "Details":"-", "Tests":"-"},
                          {"Feature":"feature 3", "Details":"-", "Tests":"-"}],
                        "Panel 2":[
                          {"Feature":"feature 4", "Details":"-", "Tests":"1281, 1282"},
                          {"Feature":"feature 5", "Details":"-", "Tests":"1283, 1285, 1622, 1623, 1383, 1384"},
                          {"Feature":"feature 6", "Details":"-", "Tests":"1621"},
                          {"Feature":"feature 7", "Details":"-", "Tests":"1624"},
                          {"Feature":"feature 8", "Details":"-", "Tests":"1626, 1627, 1819, 26476, 26598"},
                          {"Feature":"feature 9", "Details":"-", "Tests":"1625"}],
                        "Panel 3":[
                          {"Feature":"feature 10", "Details":"-", "Tests":"-"},
                          {"Feature":"feature 11", "Details":"-", "Tests":"-"}]
                       };

// Cells where conditional formatting is applied (in this case, the build columns)
var cellsToFormat = buildChecklist["winCol"] + "1:" + buildChecklist["macCol"] + buildChecklist["lastMarkableRow"];

// Colors of each status
var statusColorDict = {"OK":"#b7e1cd", "Not Tested":"#999999", "Incomplete":"#fce8b2", "problems":"#f4c7c3", "issues":"#f4c7c3"};

function conditionalFormattingRules(activeSheet, cellsToFormat) {
    var range = [activeSheet.getRange(cellsToFormat), activeSheet.getRange("B2:D2")];

    // Define conditional formatting rules
    var rule1 = app.newConditionalFormatRule().whenTextContains("ok").setBackground(statusColorDict["OK"]).setRanges(range).build();
    var rule2 = app.newConditionalFormatRule().whenTextContains("Not Tested").setBackground(statusColorDict["Not Tested"]).setRanges(range).build();
    var rule3 = app.newConditionalFormatRule().whenTextContains("Incomplete").setBackground(statusColorDict["Incomplete"]).setRanges(range).build();
    var rule4 = app.newConditionalFormatRule().whenTextContains("problem").setBackground(statusColorDict["problems"]).setRanges(range).build();
    var rule5 = app.newConditionalFormatRule().whenTextContains("issues").setBackground(statusColorDict["issues"]).setRanges(range).build();

    return [rule1, rule2, rule3, rule4, rule5];
}

function getFirstEmptyRowByColumnArray(col) {
  var ss = app.getActiveSpreadsheet();
  var column = ss.getRange(col + ':' + col);
  var values = column.getValues(); // get all data in one call
  var ct = ss.getLastRow();
  while ( values[ct] && values[ct][0] == "" ) {

    var x = ss.getRange(col + ct)
    ct--;
  }
  return (ct+2);
}

function mergeVerticalDuplicates(rowStart, rowEnd, column) {
  var ss = app.getActiveSheet();
  var col = column
  var start = rowStart; // Start row range
  var end = rowEnd;  // End of Row range
  var mergeArr = [];
  var colData = ss.getRange(start, col, end, 1).getValues().toString().split(",");
  var last = false;
  var count = -1;

  colData.forEach(function(e) {
    if (e == last){
      count++;
    }
    else if (e != last){
      mergeArr.push(count + 1);
      count = 0;
    }
    last = e;
  });

    var mergeStart = start;
    for (each = 0; each < mergeArr.length; each++) {
      var mergeEnd = mergeStart + mergeArr[each] - 1;
      if (ss.getRange(mergeStart, col).getValue() == "" ) {
      }
      else{
        if (mergeEnd - mergeStart >= 1){
          ss.getRange(mergeStart, col, mergeArr[each], 1).merge();
        }
      }
      mergeStart = mergeEnd + 1;
    }
}

function rowOfProduct(product){
  var data = testingSchedule.getDataRange().getValues();
  var productName = product;
  for(var i = 0; i<data.length;i++) {
    if(data[i][0] == productName){ //[1] because column B
      return i+1;
    }
  }
}

function setConditionalFormatting(sheet, range) {

  var arr = conditionalFormattingRules(sheet, range);
  for (var i=0; i<arr.length; i++) {
    var rules = sheet.getConditionalFormatRules();
    rules.push(arr[i]);
    sheet.setConditionalFormatRules(rules);
  }
}

function setHeaderValues(newSheet, list, buildCol, installationCol, jobServerCol, windowsCol, linuxCol, macCol) {

  // Label header cells
  newSheet.getRange(list["winCol"] + "1").setValue(testingSchedule.getRange(buildCol).getValue()).setFontWeight("bold");
  newSheet.getRange(list["winCol"] + "3").setValue("Windows\n" + testingSchedule.getRange(windowsCol).getValue());
  newSheet.getRange(list["linCol"] + "3").setValue("Linux\n" + testingSchedule.getRange(linuxCol).getValue());
  newSheet.getRange(list["macCol"] + "3").setValue("Mac\n" + testingSchedule.getRange(macCol).getValue());

  var columns = [list["winCol"], list["linCol"], list["macCol"]]

  for (col of columns) {
    // Mark cells either "Incomplete" or "Not Tested"
    if (newSheet.getRange(col + "3").getValue().indexOf("-") > -1){
    newSheet.getRange(col + "2").setValue("Not Tested");
    } else {
    newSheet.getRange(col + "2").setValue("Incomplete");

    // Add Job_server status to column w/ "Incomplete"
    var update = newSheet.getRange(col + "3").getValue() + "\n" + testingSchedule.getRange(jobServerCol).getValue() + ";" + testingSchedule.getRange(installationCol).getValue();
    newSheet.getRange(col + "3").setValue(update);
    }

    // Merge cells vertically
    newSheet.getRange(col + "3:"+ col +"4").mergeVertically();
  }
}

function setPercentages(sheet, percentRow) {
// set percent forumlas for each build column
  sheet.getRange(buildChecklist["winCol"] + percentRow).setValue("=round(counta(" + buildChecklist["winCol"] + buildChecklist["firstMarkableRow"] + ":" + buildChecklist["winCol"] + buildChecklist["lastMarkableRow"] + ")*100/(row()-" + buildChecklist["firstMarkableRow"] + "),0)")
  sheet.getRange(buildChecklist["linCol"] + percentRow).setValue("=round(counta(" + buildChecklist["linCol"] + buildChecklist["firstMarkableRow"] + ":" + buildChecklist["linCol"] + buildChecklist["lastMarkableRow"] + ")*100/(row()-" + buildChecklist["firstMarkableRow"] + "),0)")
  sheet.getRange(buildChecklist["macCol"] + percentRow).setValue("=round(counta(" + buildChecklist["macCol"] + buildChecklist["firstMarkableRow"] + ":" + buildChecklist["macCol"] + buildChecklist["lastMarkableRow"] + ")*100/(row()-" + buildChecklist["firstMarkableRow"] + "),0)")
}
