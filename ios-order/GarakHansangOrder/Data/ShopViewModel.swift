import Foundation
import Combine

/// All state is in-memory and demo-only. There are no order/payment/account network requests.
@MainActor final class ShopViewModel: ObservableObject {
    @Published var search = ""
    @Published var category: String? = nil
    @Published var favoriteIDs: Set<String> = []
    @Published var cart = PreviewCart()
    @Published var deliveryMode: ServiceMode = .delivery
    @Published var tab: ShopTab = .home
    @Published var catalogError: String? = nil

    let catalog: MenuCatalog

    init(data: Data? = nil) {
        do {
            let contents: Data
            if let data { contents = data }
            else {
                guard let url = Bundle.main.url(forResource: "menu_catalog", withExtension: "json") else {
                    throw NSError(domain: "Catalog", code: 404, userInfo: [NSLocalizedDescriptionKey: "번들에 상품 파일이 없습니다"])
                }
                contents = try Data(contentsOf: url)
            }
            catalog = try CatalogStore.decodeAndValidate(contents)
        } catch {
            // Fail closed: never allow a fabricated or orderable catalog to appear.
            catalog = MenuCatalog(brand: "가락한상 오더", version: "unavailable", notForLiveSales: true, items: [])
            catalogError = "상품 자료를 검증할 수 없습니다. 앱을 다시 설치해 주세요."
        }
    }

    var filteredItems: [MenuItem] { catalog.filtered(category: category, search: search) }
    var savedItems: [MenuItem] { catalog.items.filter { favoriteIDs.contains($0.id) } }
    var cartItems: [MenuItem] { catalog.items.filter { cart.quantity(for: $0.id) > 0 } }
    var previewTotal: Int { cart.total(catalog: catalog) }

    func chooseCategory(_ value: String?) {
        category = value
        search = "" // prevents stale search when changing categories
    }

    func toggleFavorite(_ item: MenuItem) {
        if !favoriteIDs.insert(item.id).inserted { favoriteIDs.remove(item.id) }
    }

    func addToPreview(_ item: MenuItem) { _ = cart.add(item) }
    func subtractFromPreview(_ item: MenuItem) { cart.subtract(id: item.id) }
    func removeFromPreview(_ item: MenuItem) { cart.remove(id: item.id) }
}

enum ShopTab: Int, Hashable { case home, saved, cart, account }
enum ServiceMode: String, CaseIterable, Identifiable {
    case delivery = "배달 미리보기", pickup = "포장 미리보기"
    var id: String { rawValue }
}
