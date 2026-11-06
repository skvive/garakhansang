import Foundation

public struct MenuItem: Codable, Hashable, Identifiable, Sendable {
    public let id: String
    public let category: String
    public let name: String
    public let priceKRW: Int
    public let description: String
    public let image: String
    public let catalogVisibility: String
    public let imageIsAIConcept: Bool
    public let isOrderable: Bool

    enum CodingKeys: String, CodingKey {
        case id, category, name, description, image
        case priceKRW = "price_krw"
        case catalogVisibility = "catalog_visibility"
        case imageIsAIConcept = "image_is_ai_concept"
        case isOrderable = "is_orderable"
    }

    public var imageName: String { String(image.dropLast(4)) }
}

public struct MenuCatalog: Decodable, Sendable {
    public let brand: String
    public let version: String
    public let notForLiveSales: Bool
    public let items: [MenuItem]

    enum CodingKeys: String, CodingKey {
        case brand, version, items
        case notForLiveSales = "not_for_live_sales"
    }

    public var categories: [String] {
        var seen = Set<String>()
        return items.compactMap { seen.insert($0.category).inserted ? $0.category : nil }
    }

    public func filtered(category: String?, search: String) -> [MenuItem] {
        let term = search.trimmingCharacters(in: .whitespacesAndNewlines)
        return items.filter { item in
            (category == nil || category == item.category) &&
            (term.isEmpty || item.name.localizedStandardContains(term) || item.category.localizedStandardContains(term))
        }
    }

    public func byID(_ id: String) -> MenuItem? { items.first(where: { $0.id == id }) }
}

public enum CatalogValidationError: Error, Equatable {
    case empty, duplicateID, unsafeCatalog, malformedItem
}

public enum CatalogStore {
    public static func decodeAndValidate(_ data: Data) throws -> MenuCatalog {
        let catalog = try JSONDecoder().decode(MenuCatalog.self, from: data)
        guard !catalog.items.isEmpty else { throw CatalogValidationError.empty }
        guard Set(catalog.items.map(\.id)).count == catalog.items.count else { throw CatalogValidationError.duplicateID }
        guard catalog.notForLiveSales && catalog.items.allSatisfy({ !$0.isOrderable && $0.catalogVisibility == "needs_merchandising_approval" }) else {
            throw CatalogValidationError.unsafeCatalog
        }
        guard catalog.items.allSatisfy({ item in
            !item.id.isEmpty && !item.name.isEmpty && item.priceKRW >= 0 && item.priceKRW < 100_000_000 &&
            item.image.range(of: "^menu_[0-9]{2}\\.jpg$", options: .regularExpression) != nil
        }) else { throw CatalogValidationError.malformedItem }
        return catalog
    }
}

/// This is a local, unsubmitted preview cart; no service, payment or delivery operation exists.
public struct PreviewCart: Equatable, Sendable {
    public private(set) var quantities: [String: Int] = [:]
    public static let maximumPerItem = 20
    public init() {}

    @discardableResult public mutating func add(_ item: MenuItem) -> Bool {
        guard !item.isOrderable else { return false }
        let current = quantities[item.id, default: 0]
        guard current < Self.maximumPerItem else { return false }
        quantities[item.id] = current + 1
        return true
    }

    public mutating func subtract(id: String) {
        let current = quantities[id, default: 0]
        if current <= 1 { quantities.removeValue(forKey: id) }
        else { quantities[id] = current - 1 }
    }

    public mutating func remove(id: String) { quantities.removeValue(forKey: id) }
    public mutating func clear() { quantities.removeAll() }
    public func quantity(for id: String) -> Int { quantities[id, default: 0] }
    public var count: Int { quantities.values.reduce(0, +) }
    public func total(catalog: MenuCatalog) -> Int {
        catalog.items.reduce(0) { $0 + $1.priceKRW * quantity(for: $1.id) }
    }
}
