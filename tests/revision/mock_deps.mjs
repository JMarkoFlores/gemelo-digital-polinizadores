export const utils = {
  book_new: () => {
    const wb = { SheetNames: [], Sheets: {} }
    globalThis.__lastWorkbook = wb
    return wb
  },
  json_to_sheet: (data) => ({ '!data': data, '!cols': [] }),
  book_append_sheet: (wb, ws, name) => {
    wb.SheetNames.push(name)
    wb.Sheets[name] = ws
    globalThis.__lastWorkbook = wb
  },
}
export const writeFile = (wb, filename) => {
  wb._writtenFilename = filename
  globalThis.__lastWorkbook = wb
}
export default class jsPDF {
  constructor() { this._texts = [] }
  setFillColor() {}
  setDrawColor() {}
  roundedRect() {}
  rect() {}
  setFontSize() {}
  setTextColor() {}
  setFont() {}
  text(str) { this._texts.push(str) }
  addPage() {}
  save(filename) { this._savedFilename = filename }
}
export class Document {}
export class Packer { static async toBlob() { return {} } }
export class Paragraph {}
export class Table {}
export class TableCell {}
export class TableRow {}
export class TextRun {}
export const HeadingLevel = { HEADING_1: 1, HEADING_2: 2 }
export const AlignmentType = { CENTER: 'center' }
export class ImageRun {}
export function saveAs() {}
