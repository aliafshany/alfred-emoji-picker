// Renders emoji/symbol icons for the Alfred emoji picker.
// stdin lines: "<file-stem>\t<kind e|s>\t<text>"; writes <outdir>/<file-stem>.png (128×128), skipping existing files.
// Build: swiftc -O render_icons.swift -o render_icons
import AppKit

let outDir = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "."
let side: CGFloat = 128
let emojiFont = NSFont(name: "Apple Color Emoji", size: 100) ?? NSFont.systemFont(ofSize: 100)
let symbolFont = NSFont.systemFont(ofSize: 96, weight: .medium)
let symbolColor = NSColor(white: 0.86, alpha: 1)  // readable on dark Alfred themes

try? FileManager.default.createDirectory(atPath: outDir, withIntermediateDirectories: true)

while let line = readLine() {
    let parts = line.split(separator: "\t", maxSplits: 2).map(String.init)
    guard parts.count == 3 else { continue }
    let path = outDir + "/" + parts[0] + ".png"
    if FileManager.default.fileExists(atPath: path) { continue }
    let attrs: [NSAttributedString.Key: Any] = parts[1] == "s"
        ? [.font: symbolFont, .foregroundColor: symbolColor]
        : [.font: emojiFont]
    let text = NSAttributedString(string: parts[2], attributes: attrs)
    guard let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: Int(side), pixelsHigh: Int(side),
                                     bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
                                     colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0) else { continue }
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    let box = text.boundingRect(with: NSSize(width: 1000, height: 1000), options: [.usesLineFragmentOrigin])
    let scale = min(1, side / max(box.width, box.height, 1))
    if let ctx = NSGraphicsContext.current?.cgContext {
        ctx.translateBy(x: side / 2, y: side / 2)
        ctx.scaleBy(x: scale, y: scale)
    }
    text.draw(at: NSPoint(x: -box.width / 2 - box.origin.x, y: -box.height / 2 - box.origin.y))
    NSGraphicsContext.restoreGraphicsState()
    if let png = rep.representation(using: .png, properties: [:]) {
        try? png.write(to: URL(fileURLWithPath: path))
    }
}
