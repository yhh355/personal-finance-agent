import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputPath = fileURLToPath(new URL("./demo_statement.xlsx", import.meta.url));

const rows = [
  ["WeChat Pay Statement - Synthetic Demo Data"],
  ["Billing period: 2026-09-01 to 2026-09-30"],
  ["All merchants, transaction descriptions, and amounts are fictional."],
  [],
  ["交易时间", "交易类型", "交易对方", "商品", "收/支", "金额(元)"],
  ["2026-09-01 09:15:00", "Merchant payment", "NTUC FairPrice", "Groceries", "支出", 125.00],
  ["2026-09-02 12:30:00", "Merchant payment", "GrabFood", "Lunch delivery", "支出", 28.00],
  ["2026-09-03 08:10:00", "Transport", "MRT Singapore", "MRT top-up", "支出", 45.00],
  ["2026-09-04 20:00:00", "Subscription", "Netflix", "Monthly subscription", "支出", 18.98],
  ["2026-09-05 19:30:00", "Transfer", "Social Activity", "Shared dinner payment", "支出", 120.00],
  ["2026-09-07 14:20:00", "Merchant payment", "Shopee", "Household items", "支出", 89.00],
  ["2026-09-10 19:00:00", "Merchant payment", "City Restaurant", "Dinner", "支出", 68.00],
  ["2026-09-11 21:15:00", "Transfer", "Social Activity", "Weekend outing", "支出", 150.00],
  ["2026-09-14 10:00:00", "Merchant payment", "NTUC FairPrice", "Groceries", "支出", 98.00],
  ["2026-09-16 12:15:00", "Merchant payment", "GrabFood", "Lunch delivery", "支出", 32.00],
  ["2026-09-18 20:30:00", "Entertainment", "Cinema", "Movie tickets", "支出", 30.00],
  ["2026-09-20 18:00:00", "Transfer", "Social Activity", "Group activity", "支出", 200.00],
  ["2026-09-22 08:40:00", "Transport", "City Taxi", "Taxi ride", "支出", 42.00],
  ["2026-09-24 19:30:00", "Merchant payment", "City Restaurant", "Dinner", "支出", 75.00],
  ["2026-09-26 15:10:00", "Merchant payment", "Shopee", "Personal items", "支出", 115.00],
  ["2026-09-27 21:00:00", "Transfer", "Social Activity", "Shared activity", "支出", 180.00],
  ["2026-09-29 09:00:00", "Merchant payment", "Coffee Shop", "Coffee", "支出", 24.00],
  ["2026-09-30 18:30:00", "Utilities", "Utility Provider", "Utilities", "支出", 70.00],
  ["2026-09-30 23:00:00", "Transfer", "Demo Income", "Ignored income row", "收入", 500.00],
];

const workbook = Workbook.create();
const sheet = workbook.worksheets.add("Statement");
sheet.showGridLines = false;
sheet.getRange("A1:F24").values = rows;
sheet.mergeCells("A1:F1");
sheet.mergeCells("A2:F2");
sheet.mergeCells("A3:F3");
sheet.getRange("A1:F1").format = {
  fill: "#1F4E78",
  font: { name: "Arial", size: 14, bold: true, color: "#FFFFFF" },
  horizontalAlignment: "left",
  verticalAlignment: "center",
};
sheet.getRange("A2:F3").format = {
  font: { name: "Arial", size: 10, italic: true, color: "#404040" },
  wrapText: true,
};
sheet.getRange("A5:F5").format = {
  fill: "#4472C4",
  font: { name: "Arial", size: 10, bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  borders: { preset: "all", style: "thin", color: "#D9E2F3" },
};
sheet.getRange("A6:F24").format = {
  font: { name: "Arial", size: 10, color: "#000000" },
  borders: { preset: "insideHorizontal", style: "thin", color: "#E7E6E6" },
};
sheet.getRange("A6:A24").format.numberFormat = "yyyy-mm-dd hh:mm";
sheet.getRange("F6:F24").format.numberFormat = "0.00";
sheet.getRange("A:A").format.columnWidth = 21;
sheet.getRange("B:B").format.columnWidth = 18;
sheet.getRange("C:C").format.columnWidth = 20;
sheet.getRange("D:D").format.columnWidth = 24;
sheet.getRange("E:E").format.columnWidth = 10;
sheet.getRange("F:F").format.columnWidth = 12;
sheet.getRange("A1:F1").format.rowHeight = 26;
sheet.freezePanes.freezeRows(5);

const preview = await workbook.render({ sheetName: "Statement", range: "A1:F24", scale: 1.5, format: "png" });
await fs.writeFile(new URL("./demo_statement_preview.png", import.meta.url), new Uint8Array(await preview.arrayBuffer()));
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);
