// Don't forget to go to "Triggers" in script editor and add a trigger where automationMenu() is triggered when the spreadsheet is opened

function automationMenu() {
  SpreadsheetApp.getUi().createMenu("CoreQA Checklist Automation")
  .addItem('Create new regression checklist', 'createNewChecklist')
  .addItem('Update checklist to the next build', 'updateChecklist')
  .addItem('Mark all cells as OK', 'markAllOk')
  .addToUi();

}
