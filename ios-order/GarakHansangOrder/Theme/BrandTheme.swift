import SwiftUI

enum BrandTheme {
    static let brown = Color(red: 87/255, green: 45/255, blue: 38/255)
    static let red = Color(red: 133/255, green: 55/255, blue: 43/255)
    static let cream = Color(red: 247/255, green: 239/255, blue: 219/255)
    static let canvas = Color(red: 253/255, green: 250/255, blue: 244/255)
    static let muted = Color(red: 116/255, green: 107/255, blue: 96/255)
    static let sea = Color(red: 45/255, green: 84/255, blue: 97/255)
    static let positive = Color(red: 55/255, green: 109/255, blue: 84/255)
}

extension Int {
    var krwText: String { formatted(.number.locale(Locale(identifier: "ko_KR"))) + "원" }
}

struct DemoFlag: View {
    var body: some View {
        Label("시연용 · 실제 주문 불가", systemImage: "lock.shield")
            .font(.caption2.weight(.semibold))
            .foregroundStyle(BrandTheme.red)
            .padding(.horizontal, 11)
            .padding(.vertical, 7)
            .background(BrandTheme.cream, in: Capsule())
            .accessibilityLabel("시연용 화면입니다. 실제 주문 및 결제는 불가능합니다")
    }
}
