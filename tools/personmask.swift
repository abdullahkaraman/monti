// Writes a refined person mask (white = person) for each image into OUT_DIR, same file name, as grayscale PNG.
// Combines macOS 14+ VNGenerateForegroundInstanceMaskRequest (high-res hair/edge detail)
// with VNGeneratePersonSegmentationRequest (person-only gate + hole-free interior)
// and motion-safe temporal smoothing to reduce edge flicker across video frames.
// usage: personmask OUT_DIR img1.png img2.png ...
import Foundation
import Vision
import ImageIO
import CoreImage
import UniformTypeIdentifiers

let args = CommandLine.arguments
guard args.count > 2 else { print("usage: personmask OUT_DIR images..."); exit(1) }
let outDir = URL(fileURLWithPath: args[1])
let ctx = CIContext(options: [.workingColorSpace: NSNull()])

let personReq = VNGeneratePersonSegmentationRequest()
personReq.qualityLevel = .accurate
personReq.outputPixelFormat = kCVPixelFormatType_OneComponent8

func scaleToFit(_ img: CIImage, width: Int, height: Int) -> CIImage {
    let sx = CGFloat(width) / img.extent.width
    let sy = CGFloat(height) / img.extent.height
    return img.transformed(by: CGAffineTransform(scaleX: sx, y: sy))
        .cropped(to: CGRect(x: 0, y: 0, width: width, height: height))
}

func morph(_ img: CIImage, name: String, radius: Float, extent: CGRect) -> CIImage {
    guard let f = CIFilter(name: name) else { return img }
    f.setValue(img.clampedToExtent(), forKey: kCIInputImageKey)
    f.setValue(radius, forKey: kCIInputRadiusKey)
    return (f.outputImage ?? img).cropped(to: extent)
}

func multiply(_ a: CIImage, _ b: CIImage, extent: CGRect) -> CIImage {
    guard let f = CIFilter(name: "CIMultiplyCompositing") else { return a }
    f.setValue(a, forKey: kCIInputImageKey)
    f.setValue(b, forKey: kCIInputBackgroundImageKey)
    return (f.outputImage ?? a).cropped(to: extent)
}

func maximum(_ a: CIImage, _ b: CIImage, extent: CGRect) -> CIImage {
    guard let f = CIFilter(name: "CIMaximumCompositing") else { return a }
    f.setValue(a, forKey: kCIInputImageKey)
    f.setValue(b, forKey: kCIInputBackgroundImageKey)
    return (f.outputImage ?? a).cropped(to: extent)
}

let grayCS = CGColorSpaceCreateDeviceGray()
var prevBytes: [UInt8]? = nil
var prevW = 0
var prevH = 0

for path in args.dropFirst(2) {
    let url = URL(fileURLWithPath: path)
    guard let src = CGImageSourceCreateWithURL(url as CFURL, nil),
          let img = CGImageSourceCreateImageAtIndex(src, 0, nil) else { print(path, "unreadable"); continue }
    let w = img.width, h = img.height
    let extent = CGRect(x: 0, y: 0, width: w, height: h)
    let handler = VNImageRequestHandler(cgImage: img, options: [:])

    do { try handler.perform([personReq]) } catch { print(path, "person failed:", error); continue }
    guard let pBuf = personReq.results?.first?.pixelBuffer else { print(path, "no person"); continue }
    let personMask = scaleToFit(CIImage(cvPixelBuffer: pBuf), width: w, height: h)

    var finalMask = personMask

    if #available(macOS 14.0, *) {
        let fgReq = VNGenerateForegroundInstanceMaskRequest()
        if (try? handler.perform([fgReq])) != nil,
           let obs = fgReq.results?.first,
           !obs.allInstances.isEmpty,
           let fgBuf = try? obs.generateScaledMaskForImage(forInstances: obs.allInstances, from: handler) {
            let fgMask = scaleToFit(CIImage(cvPixelBuffer: fgBuf), width: w, height: h)
            // Scale morphology radii proportionally to image width (tight 5px halo: catches fine hair, blocks laptop/desk bleed)
            let scale = Float(w) / 1080.0
            let outerGate = morph(personMask, name: "CIMorphologyMaximum", radius: max(3, 5 * scale), extent: extent)
            let interior = morph(personMask, name: "CIMorphologyMinimum", radius: max(4, 6 * scale), extent: extent)
            let gatedFg = multiply(fgMask, outerGate, extent: extent)
            finalMask = maximum(interior, gatedFg, extent: extent)
        }
    }

    var bytes = [UInt8](repeating: 0, count: w * h)
    ctx.render(finalMask, toBitmap: &bytes, rowBytes: w, bounds: extent, format: .L8, colorSpace: grayCS)

    // Motion-safe temporal smoothing: only blend small edge flickers, never fast movement.
    if let prev = prevBytes, prevW == w, prevH == h {
        for i in 0..<bytes.count {
            let c = Int(bytes[i])
            let p = Int(prev[i])
            let diff = abs(c - p)
            if diff > 0 && diff < 45 {
                bytes[i] = UInt8((c * 65 + p * 35) / 100)
            }
        }
    }
    prevBytes = bytes
    prevW = w
    prevH = h

    let data = Data(bytes)
    guard let provider = CGDataProvider(data: data as CFData),
          let cg = CGImage(width: w, height: h, bitsPerComponent: 8, bitsPerPixel: 8, bytesPerRow: w,
                           space: grayCS, bitmapInfo: CGBitmapInfo(rawValue: 0), provider: provider,
                           decode: nil, shouldInterpolate: false, intent: .defaultIntent),
          let out = CGImageDestinationCreateWithURL(outDir.appendingPathComponent(url.lastPathComponent) as CFURL,
                                                    UTType.png.identifier as CFString, 1, nil)
    else { print(path, "write failed"); continue }
    CGImageDestinationAddImage(out, cg, nil)
    CGImageDestinationFinalize(out)
}
