import Foundation
import SwiftUI

@MainActor
final class CatalogStore: ObservableObject {
    @Published private(set) var items: [CatalogItem] = []
    @Published private(set) var loadError: String? = nil
    @Published private(set) var favorites: Set<String> = []
    @Published private(set) var cart: [String: Int] = [:]
    @Published var searchQuery = ""
    @Published var selectedCategory: String? = nil
    @Published var fulfillment: Fulfillment = .delivery

    enum Fulfillment: String, CaseIterable, Identifiable {
        case delivery = "배달 미리보기"
        case pickup = "포장 미리보기"
        var id: String { rawValue }
    }

    init() {
        do {
            guard let url = Bundle.main.url(forResource: "menus_47", withExtension: "json", subdirectory: "Resources/Catalog") else {
                throw NSError(domain: "OfflineCatalog", code: 404)
            }
            items = try OfflineCatalog.load(Data(contentsOf: url)).items
        } catch {
            items = []
            loadError = "상품 자료를 열 수 없습니다. 이 앱에서는 주문할 수 없습니다."
        }
    }

    var categories: [String] {
        var seen = Set<String>()
        return items.map(\.category).filter { seen.insert($0).inserted }
    }
    var displayedItems: [CatalogItem] {
        items.filter { item in
            let cat = selectedCategory == nil || selectedCategory == item.category
            let q = searchQuery.trimmingCharacters(in: .whitespacesAndNewlines)
            let search = q.isEmpty || item.name.localizedStandardContains(q) || item.category.localizedStandardContains(q)
            return cat && search
        }
    }
    var savedItems: [CatalogItem] { items.filter { favorites.contains($0.id) } }
    struct CartLine: Identifiable {
        let item: CatalogItem
        let quantity: Int
        var id: String { item.id }
    }
    var cartItems: [CartLine] { items.compactMap { item in
        guard let q = cart[item.id], q > 0 else { return nil }
        return CartLine(item: item, quantity: q)
    }}
    var itemCount: Int { cart.values.reduce(0, +) }
    var subtotal: Int { cartItems.reduce(0) { $0 + ($1.item.price_krw * $1.quantity) } }

    func toggleFavorite(_ item: CatalogItem) {
        if favorites.contains(item.id) { favorites.remove(item.id) }
        else { favorites.insert(item.id) }
    }
    func addDemo(_ item: CatalogItem) {
        guard items.contains(where: { $0.id == item.id }), !item.is_orderable else { return }
        cart[item.id] = min(99, (cart[item.id] ?? 0) + 1)
    }
    func decrementDemo(_ item: CatalogItem) {
        guard let n = cart[item.id] else { return }
        if n <= 1 { cart.removeValue(forKey: item.id) }
        else { cart[item.id] = n - 1 }
    }
    func clearDemo() { cart.removeAll() }
    func selectCategory(_ category: String?) {
        selectedCategory = category
        searchQuery = "" // do not leak an old category's query into a new one
    }
}
