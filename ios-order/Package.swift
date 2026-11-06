// swift-tools-version: 5.9
import PackageDescription
let package = Package(
    name: "GarakHansangOrderDomain",
    platforms: [.iOS(.v16)],
    products: [.library(name: "GarakHansangOrderDomain", targets: ["GarakHansangOrderDomain"])],
    targets: [
        .target(name: "GarakHansangOrderDomain", path: "Shared", resources: [.process("Resources")]),
        .testTarget(name: "GarakHansangOrderDomainTests", dependencies: ["GarakHansangOrderDomain"], path: "Tests/GarakHansangOrderDomainTests")
    ]
)
