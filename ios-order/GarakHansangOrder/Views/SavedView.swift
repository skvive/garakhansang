import SwiftUI

struct SavedView: View {
    @EnvironmentObject private var model: ShopViewModel
    @State private var selected: MenuItem?
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                DemoFlag().padding(.top, 16)
                if model.savedItems.isEmpty {
                    EmptyViewMessage(symbol: "heart", headline: "찜한 메뉴가 없습니다", hint: "홈에서 마음에 드는 메뉴를 찜해 보세요.")
                } else {
                    ForEach(model.savedItems) { item in
                        ProductRow(item: item,
                                   isFavorite: true,
                                   quantity: model.cart.quantity(for: item.id),
                                   onOpen: { selected = item },
                                   onFavorite: { model.toggleFavorite(item) },
                                   onAdd: { model.addToPreview(item) })
                    }
                }
            }
            .padding(.horizontal, 16).padding(.bottom, 24)
        }
        .background(BrandTheme.canvas.ignoresSafeArea())
        .navigationTitle("찜한 메뉴")
        .sheet(item: $selected) { item in NavigationStack { ProductDetailView(item: item) } }
    }
}
