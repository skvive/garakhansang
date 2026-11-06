import SwiftUI

@main
struct GarakHansangOrderApp: App {
    @StateObject private var store = CatalogStore()

    var body: some Scene {
        WindowGroup {
            RootTabView()
                .environmentObject(store)
                .tint(Brand.brown)
        }
    }
}
