// Reads one emoji per line on stdin; prints the ones this Mac can't draw: any part lands on
// LastResort, the font that draws the "?" box. Symbols drawn by a text font (→ • «) are fine.
// Glyph counts are no guide: a couple-with-heart draws correctly from two glyphs.
import CoreText
import Foundation

let font = CTFontCreateWithName("AppleColorEmoji" as CFString, 32, nil)
let data = FileHandle.standardInput.readDataToEndOfFile()
for glyph in (String(data: data, encoding: .utf8) ?? "").split(separator: "\n") {
    let attributed = NSAttributedString(string: String(glyph), attributes: [kCTFontAttributeName as NSAttributedString.Key: font])
    let line = CTLineCreateWithAttributedString(attributed)
    let runs = CTLineGetGlyphRuns(line) as! [CTRun]
    var lastResort = false
    for run in runs {
        let attributes = CTRunGetAttributes(run) as NSDictionary
        if let used = attributes[kCTFontAttributeName] {
            let name = CTFontCopyPostScriptName(used as! CTFont) as String
            if name == "LastResort" { lastResort = true }
        }
    }
    if lastResort { print(glyph) }
}
