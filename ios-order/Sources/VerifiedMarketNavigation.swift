import Foundation

/// Shared Garakland navigation policy port for the iOS customer demo.
/// Coordinates must be verified and must never be inferred from images,
/// merchant names or an unapproved/placeholder product listing.
enum VerifiedMarketNavigation {
    static let marketAddress = "서울특별시 송파구 양재대로 932 가락시장"
    static let marketName = "가락시장"

    struct Destination {
        let name: String
        let latitude: Double?
        let longitude: Double?
        let coordinateVerified: Bool
        let isDemo: Bool
    }
    enum TravelMode: String {
        case walking
        case driving
        case transit
    }
    struct Route {
        let url: URL
        let verified: Bool
        let label: String
    }
    static func hasVerifiedCoordinate(_ destination: Destination?) -> Bool {
        guard let item = destination,
              item.coordinateVerified, !item.isDemo,
              let latitude = item.latitude, let longitude = item.longitude
        else { return false }
        return latitude.isFinite && longitude.isFinite
            && latitude >= -90 && latitude <= 90
            && longitude >= -180 && longitude <= 180
            && !(latitude == 0 && longitude == 0)
    }

    static func directions(
        to destination: Destination? = nil,
        travelMode: TravelMode = .walking
    ) -> Route? {
        let verified = hasVerifiedCoordinate(destination)
        let point: String
        let label: String
        if verified, let latitude = destination?.latitude, let longitude = destination?.longitude {
            point = String(latitude) + "," + String(longitude)
            label = destination?.name ?? marketName
        } else {
            point = marketAddress
            label = marketName + " (매장 좌표 미검증)"
        }
        var components = URLComponents()
        components.scheme = "https"
        components.host = "www.google.com"
        components.path = "/maps/dir/"
        components.queryItems = [
            URLQueryItem(name: "api", value: "1"),
            URLQueryItem(name: "destination", value: point),
            URLQueryItem(name: "travelmode", value: travelMode.rawValue)
        ]
        guard let url = components.url else { return nil }
        return Route(url: url, verified: verified, label: label)
    }
}
