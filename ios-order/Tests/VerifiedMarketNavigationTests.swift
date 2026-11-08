import Foundation

/// Standalone first-party Swift verification run on macOS before Xcode simulator build.
@main
struct VerifiedMarketNavigationTests {
    static func main() {
        let defaultRoute = VerifiedMarketNavigation.directions()
        precondition(defaultRoute != nil)
        precondition(defaultRoute!.verified == false)
        precondition(defaultRoute!.url.scheme == "https")
        precondition(defaultRoute!.url.host == "www.google.com")
        let fallback = URLComponents(url: defaultRoute!.url, resolvingAgainstBaseURL: false)!
        let query = Dictionary(uniqueKeysWithValues: fallback.queryItems!.map { ($0.name, $0.value ?? "") })
        precondition(query["api"] == "1")
        precondition(query["destination"] == VerifiedMarketNavigation.marketAddress)
        precondition(query["travelmode"] == "walking")
        let verified = VerifiedMarketNavigation.Destination(
            name: "검증된 매장", latitude: 37.494321,
            longitude: 127.112345, coordinateVerified: true, isDemo: false)
        precondition(VerifiedMarketNavigation.hasVerifiedCoordinate(verified))
        let driving = VerifiedMarketNavigation.directions(to: verified, travelMode: .driving)!
        precondition(driving.verified)
        let drivingURL = URLComponents(url: driving.url, resolvingAgainstBaseURL: false)!
        let params = Dictionary(uniqueKeysWithValues: drivingURL.queryItems!.map { ($0.name, $0.value ?? "") })
        precondition(params["destination"] == "37.494321,127.112345")
        precondition(params["travelmode"] == "driving")
        let unverified = VerifiedMarketNavigation.Destination(
            name: "검증 전 매장", latitude: 37.494321, longitude: 127.112345,
            coordinateVerified: false, isDemo: false)
        precondition(VerifiedMarketNavigation.directions(to: unverified)!.verified == false)
        let demo = VerifiedMarketNavigation.Destination(
            name: "시연 매장", latitude: 37.494321, longitude: 127.112345,
            coordinateVerified: true, isDemo: true)
        precondition(VerifiedMarketNavigation.directions(to: demo)!.verified == false)
        let missing = VerifiedMarketNavigation.Destination(
            name: "좌표 없음", latitude: nil, longitude: nil,
            coordinateVerified: true, isDemo: false)
        precondition(VerifiedMarketNavigation.hasVerifiedCoordinate(missing) == false)
        let zero = VerifiedMarketNavigation.Destination(
            name: "좌표 이상", latitude: 0, longitude: 0,
            coordinateVerified: true, isDemo: false)
        precondition(VerifiedMarketNavigation.hasVerifiedCoordinate(zero) == false)
        let invalid = VerifiedMarketNavigation.Destination(
            name: "범위 초과", latitude: 91, longitude: 200,
            coordinateVerified: true, isDemo: false)
        precondition(VerifiedMarketNavigation.hasVerifiedCoordinate(invalid) == false)
        let infinity = VerifiedMarketNavigation.Destination(
            name: "값 오류", latitude: .infinity, longitude: 120,
            coordinateVerified: true, isDemo: false)
        precondition(VerifiedMarketNavigation.hasVerifiedCoordinate(infinity) == false)
        precondition(VerifiedMarketNavigation.directions(to: demo, travelMode: .transit)!.url.absoluteString.contains("transit"))
        print("PASS iOS Garakland navigation: HTTPS, market fallback, verified GPS, demo/invalid coordinate rejection, all 13 checks")
    }
}
