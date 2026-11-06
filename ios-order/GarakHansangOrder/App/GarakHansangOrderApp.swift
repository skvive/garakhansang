import SwiftUI

@main struct GarakHansangOrderApp: App {
    @StateObject private var model = ShopViewModel()
    var body: some Scene {
        WindowGroup {
            TabView(selection: $model.tab) {
                NavigationStack { HomeView() }
                    .tabItem { Label("홈", systemImage: "house.fill") }.tag(ShopTab.home)
                NavigationStack { SavedView() }
                    .tabItem { Label("찜", systemImage: "heart") }.tag(ShopTab.saved)
                NavigationStack { CartView() }
                    .tabItem { Label("장바구니", systemImage: "bag") }.tag(ShopTab.cart)
                NavigationStack { AccountView() }
                    .tabItem { Label("마이", systemImage: "person.crop.circle") }.tag(ShopTab.account)
            }
            .tint(BrandTheme.red)
            .environmentObject(model)
        }
    }
}
