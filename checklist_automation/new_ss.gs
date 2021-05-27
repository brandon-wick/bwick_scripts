function createNewChecklist() {

  // Get spreadsheet and sheet
  var ss = app.getActiveSpreadsheet();

  // Create a sheet labeled after latest release found from the testing schedule
  ss.insertSheet(testingSchedule.getSheetName());
  var newSheet = ss.getSheetByName(testingSchedule.getSheetName());

  // Set borders
  newSheet.getRangeList(buildChecklist["borders"]).setBorder(true, true, true, true, false, false, 'black', app.BorderStyle.SOLID);
  newSheet.getRangeList(checklistBorders).setBorder(true, true, true, true, false, false, 'black', app.BorderStyle.SOLID);

  // Set Conditional Formatting
  setConditionalFormatting(newSheet, cellsToFormat);

  // Set product label
  for (column in productLabel) {
    for (row = 0; row < 4; row++) {
      var cell = column + Object.keys(productLabel[column])[row]
      var value = productLabel[column][Object.keys(productLabel[column])[row]]
      newSheet.getRange(cell).setValue(value)
    };
  };

  // Set Build A
  newSheet.getRange(buildChecklist["winCol"] + "1:" + buildChecklist["macCol"] + "1").mergeAcross();
  setHeaderValues(newSheet, buildChecklist, "C1", ("G" + productRow), ("F" + productRow), ("C" + productRow), ("D" + productRow), ("E" + productRow));

  // Remove excess rows
  var removeRowStart = parseInt(buildChecklist["percentRow"])
  var rowsToDelete = newSheet.getMaxRows() - removeRowStart
  newSheet.deleteRows(removeRowStart, rowsToDelete)

  // Remove excess columns
  var colToDelete = 26 - newSheet.getLastColumn()
  var removeColStart = 1 + newSheet.getLastColumn()
  newSheet.deleteColumns(removeColStart, colToDelete)

  // Set productCheckList
  for (section in productCheckList) {
    for (item of productCheckList[section]) {
      newSheet.getRange("A" + String(getFirstEmptyRowByColumnArray("A"))).setValue(section);
      newSheet.getRange("B" + String(getFirstEmptyRowByColumnArray("B"))).setValue(item["Feature"]);
      newSheet.getRange("C" + String(getFirstEmptyRowByColumnArray("C"))).setValue(item["Details"]);
      newSheet.getRange("D" + String(getFirstEmptyRowByColumnArray("D"))).setValue(item["Tests"]);
    }
  }

  // Set percentage label
  newSheet.getRange("A" + buildChecklist["percentRow"]).setValue("Percent complete")
  newSheet.getRange("B" + buildChecklist["percentRow"]).setValue("Calculates the percent complete")
  newSheet.getRange("C" + buildChecklist["percentRow"]).setValue("-")
  newSheet.getRange("D" + buildChecklist["percentRow"]).setValue("=row()")

  // set percent forumlas
  setPercentages(newSheet, buildChecklist["percentRow"])

  //freeze rows and columns
  newSheet.setFrozenColumns(Object.keys(productLabel).length)
  newSheet.setFrozenRows(Object.keys(productLabel["A"]).length)

  // center all cells
  newSheet.getRange("A1:" + buildChecklist["macCol"] + buildChecklist["percentRow"]).setHorizontalAlignment("center").setVerticalAlignment("middle").setWrap(true);

  // Bold cells
  newSheet.getRangeList(["A1:D1", "A1:A" + buildChecklist["percentRow"]]).setFontWeight("bold").setFontSize(12)

  // set grey background
  newSheet.getRange("A1:" + buildChecklist["macCol"] + "4").setBackground("#d9d9d9")

  // format product name cell
  newSheet.getRange("A1").setBackground("orange").setFontSize(14)

  // Set product label column width
  newSheet.setColumnWidths(1, Object.keys(productLabel).length, 160);

  // Set build header column width
  newSheet.setColumnWidths(5, 3, 120);

  // merge sections in column A
  mergeVerticalDuplicates(parseInt(buildChecklist["firstMarkableRow"]), parseInt(buildChecklist["lastMarkableRow"]), 1)

}
