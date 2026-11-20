import Foundation

// 1:1 counterpart of the Android offline menu catalog. This is NOT a sales feed.
struct CatalogItem: Codable, Identifiable, Hashable {
    let id: String
    let category: String
    let name: String
    let price_krw: Int
    let description: String
    let image: String
    let catalog_visibility: String
    let image_is_ai_concept: Bool
    let source_visibility_note: String?
    let review_event_note: String?
    let source_type: String?
    let is_orderable: Bool

    var won: String { price_krw.formatted(.number) + "원" }
}

struct CatalogEnvelope: Codable {
    let brand: String
    let version: String
    let not_for_live_sales: Bool
    let items: [CatalogItem]
}

enum OfflineCatalog {
    static func load(_ data: Data) throws -> CatalogEnvelope {
        let envelope = try JSONDecoder().decode(CatalogEnvelope.self, from: data)
        guard envelope.not_for_live_sales,
              envelope.items.count == 47,
              Set(envelope.items.map(\.id)).count == 47,
              envelope.items.allSatisfy({ !$0.is_orderable && $0.image_is_ai_concept &&
                  $0.catalog_visibility == "needs_merchandising_approval" }) else {
            throw CatalogError.unsafeOrIncomplete
        }
        return envelope
    }

    enum CatalogError: LocalizedError {
        case unsafeOrIncomplete
        var errorDescription: String? { "시연 전용 47개 상품 데이터 검증에 실패했습니다." }
    }
}
