// Writes a person mask (white = person) for each image into OUT_DIR, same file name, as grayscale PNG.
// usage: personmask OUT_DIR img1.png img2.png ...
import Foundation
import Vision
import ImageIO
import CoreImage
import UniformTypeIdentifiers

let args = CommandLine.arguments
guard args.count > 2 else { print("usage: personmask OUT_DIR images..."); exit(1) }
let outDir = URL(fileURLWithPath: args[1])
let ctx = CIContext()
let req = VNGeneratePersonSegmentationRequest()
req.qualityLevel = .accurate
req.outputPixelFormat = kCVPixelFormatType_OneComponent8

for path in args.dropFirst(2) {
    let url = URL(fileURLWithPath: path)
    guard let src = CGImageSourceCreateWithURL(url as CFURL, nil),
          let img = CGImageSourceCreateImageAtIndex(src, 0, nil) else { print(path, "unreadable"); continue }
    do { try VNImageRequestHandler(cgImage: img).perform([req]) } catch { print(path, "failed:", error); continue }
    guard let buf = req.results?.first?.pixelBuffer else { print(path, "no person"); continue }
    // Scale the low-resolution mask up to the image size so it lines up pixel for pixel.
    var mask = CIImage(cvPixelBuffer: buf)
    mask = mask.transformed(by: CGAffineTransform(scaleX: CGFloat(img.width) / mask.extent.width,
                                                  y: CGFloat(img.height) / mask.extent.height))
    let dest = outDir.appendingPathComponent(url.lastPathComponent)
    guard let cg = ctx.createCGImage(mask, from: CGRect(x: 0, y: 0, width: img.width, height: img.height),
                                     format: .L8, colorSpace: CGColorSpaceCreateDeviceGray()),
          let out = CGImageDestinationCreateWithURL(dest as CFURL, UTType.png.identifier as CFString, 1, nil)
    else { print(path, "write failed"); continue }
    CGImageDestinationAddImage(out, cg, nil)
    CGImageDestinationFinalize(out)
}
