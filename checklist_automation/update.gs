function updateChecklist() {

  // Get spreadsheet and sheet
  var ss = app.getActiveSpreadsheet();
  var activeSheet = ss.getActiveSheet();

  // Insert columns
  activeSheet.insertColumnsAfter(Object.keys(productLabel).length, 3);

  // Set column width
  activeSheet.setColumnWidths(Object.keys(productLabel).length + 1, 3, 120);

  // Clear all formatting and align text
  activeSheet.getRange(cellsToFormat).clear();
  activeSheet.getRange(cellsToFormat).setHorizontalAlignment("center").setVerticalAlignment("middle");

  // Set background to grey
  activeSheet.getRangeList([buildChecklist["winCol"] +"1:" + buildChecklist["macCol"] + "4"]).setBackground("#d9d9d9");

  // Merge cells
  activeSheet.getRange(buildChecklist["winCol"] + "1:" + buildChecklist["macCol"] + "1").mergeAcross();

  // Set percentage row
  setPercentages(activeSheet, buildChecklist["percentRow"]);

  // Set borders
  activeSheet.getRangeList(buildChecklist["borders"]).setBorder(true, true, true, true, false, false, 'black', app.BorderStyle.SOLID);

  // Set Header cells
  if (activeSheet.getMaxColumns() <= 8) {
  // set build-A
  setHeaderValues(activeSheet, buildChecklist, "C1", ("G" + productRow), ("F" +  productRow), ("C" + productRow), ("D"+ productRow), ("E" + productRow));
  } else if (8 < activeSheet.getMaxColumns() && activeSheet.getMaxColumns() <= 11) {
  // set build-B
  setHeaderValues(activeSheet, buildChecklist, "H1", ("L" + productRow), ("K" +  productRow), ("H" + productRow), ("I"+ productRow), ("J" + productRow));
  } else if (11 < activeSheet.getMaxColumns() && activeSheet.getMaxColumns() <= 14) {
  // set build-C
  setHeaderValues(activeSheet, buildChecklist, "M1", ("Q" + productRow), ("P" +  productRow), ("M" + productRow), ("N"+ productRow), ("O" + productRow));
  } else if (14 < activeSheet.getMaxColumns() && activeSheet.getMaxColumns() <= 17) {
  // set build-D
  setHeaderValues(activeSheet, buildChecklist, "R1", ("V" + productRow), ("U" +  productRow), ("R" + productRow), ("S"+ productRow), ("T" + productRow));
  } else if (17 < activeSheet.getMaxColumns() && activeSheet.getMaxColumns() <= 20) {
  // set build-E
  setHeaderValues(activeSheet, buildChecklist, "W1", ("AA" + productRow), ("Z" +  productRow), ("W" + productRow), ("X"+ productRow), ("Y" + productRow));
  } else if (20 < activeSheet.getMaxColumns()) {
  // set build-F
  setHeaderValues(activeSheet, buildChecklist, "AB1", ("AF" + productRow), ("AE" +  productRow), ("AB" + productRow), ("AC"+ productRow), ("AD" + productRow));
  }

  // Set conditional formatting
  setConditionalFormatting(activeSheet, cellsToFormat);

}
