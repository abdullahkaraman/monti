// Prints the largest face box of each image as "path cx cy size" in pixels (top-left origin).
// usage: faces img1.png img2.png ...
import Foundation
import Vision
import ImageIO

for path in CommandLine.arguments.dropFirst() {
    guard let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, nil),
          let img = CGImageSourceCreateImageAtIndex(src, 0, nil) else { print(path, "none"); continue }
    let req = VNDetectFaceRectanglesRequest()
    try? VNImageRequestHandler(cgImage: img).perform([req])
    guard let f = (req.results ?? []).max(by: { $0.boundingBox.width < $1.boundingBox.width }) else { print(path, "none"); continue }
    let W = Double(img.width), H = Double(img.height), b = f.boundingBox
    print(path, Int(b.midX * W), Int((1 - b.midY) * H), Int(max(b.width * W, b.height * H)))
}
