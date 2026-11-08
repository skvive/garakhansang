import Foundation

/// Native iPhone catalog contract shared with the GarakHansang website.
/// Only products that passed ALL Neon release-evidence checks may appear here.
/// A visible product must never imply that payments or courier dispatch work.
struct VerifiedCatalogProduct: Identifiable, Codable, Equatable {
    let id: String
    let sku: String
    let merchant_id: String
    let merchant_name: String
    let name: String
    let description: String
    let category_id: String
    let category_name: String
    let price_krw: Int
    let currency: String
    let stock: Int
    let image_url: URL
    let merchant_verified: Bool
    let can_checkout: Bool
}

struct VerifiedCatalogEnvelope: Codable {
    let schema_version: Int
    let source: String
    let items: [VerifiedCatalogProduct]
    let count: Int
    let order_service_ready: Bool
    let delivery_tracking_ready: Bool
    let refresh_seconds: Int
}

enum VerifiedCatalogPolicy {
    enum Failure: Error, Equatable {
        case unexpectedSource, unverifiedItem, duplicateSKU, excessiveItems
    }

    static func decode(_ data: Data) throws -> VerifiedCatalogEnvelope {
        let catalog = try JSONDecoder().decode(VerifiedCatalogEnvelope.self, from: data)
        guard catalog.schema_version == 1,
              catalog.source == "verified_neon_release_ready",
              !catalog.order_service_ready, !catalog.delivery_tracking_ready
        else { throw Failure.unexpectedSource }
        guard catalog.items.count <= 500 && catalog.count == catalog.items.count
        else { throw Failure.excessiveItems }
        var ids = Set<String>()
        for p in catalog.items {
            guard p.merchant_verified && !p.can_checkout && p.currency == "KRW",
                  p.price_krw > 0 && p.price_krw <= 100_000_000 && p.stock > 0,
                  p.image_url.scheme?.lowercased() == "https",
                  p.image_url.host != nil && p.image_url.user == nil && p.image_url.password == nil,
                  p.id == p.sku && p.name.count > 0 && p.name.count <= 160
            else { throw Failure.unverifiedItem }
            guard ids.insert(p.sku).inserted else { throw Failure.duplicateSKU }
        }
        return catalog
    }
}
