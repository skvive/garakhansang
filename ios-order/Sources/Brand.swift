import SwiftUI
import UIKit

enum Brand {
    static let brown = Color(red: 87/255, green: 45/255, blue: 38/255)
    static let red = Color(red: 133/255, green: 55/255, blue: 43/255)
    static let cream = Color(red: 247/255, green: 239/255, blue: 219/255)
    static let teal = Color(red: 45/255, green: 84/255, blue: 97/255)
    static let canvas = Color(red: 255/255, green: 253/255, blue: 248/255)
}

struct BundledImage: View {
    let filename: String
    let subdirectory: String
    var contentMode: ContentMode = .fill

    var body: some View {
        Group {
            if let path = Bundle.main.path(forResource: filename, ofType: nil, inDirectory: "GHSContent/" + subdirectory),
               let image = UIImage(contentsOfFile: path) {
                Image(uiImage: image)
                    .resizable()
                    .aspectRatio(contentMode: contentMode)
            } else {
                Rectangle().fill(Brand.cream)
                    .overlay(Image(systemName: "photo").foregroundStyle(Brand.brown))
            }
        }
        .accessibilityLabel(filename == "garakhansang-logo.png" ? "가락한상 공식 로고" : "메뉴 이미지 참고용")
    }
}

struct DemoNotice: View {
    var compact = false
    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "info.circle.fill").font(.system(size: 16))
            Text(compact ? "시연 앱 · 실제 주문/결제 불가" :
                "시연 전용 · 메뉴 이미지와 가격은 참고용이며 실제 주문·결제·배달은 지원하지 않습니다.")
                .font(.system(size: compact ? 12 : 13, weight: .medium))
                .fixedSize(horizontal: false, vertical: true)
        }
        .foregroundStyle(Brand.brown)
        .padding(.horizontal, 13).padding(.vertical, 11)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Brand.cream.opacity(0.72), in: RoundedRectangle(cornerRadius: 13))
        .accessibilityElement(children: .combine)
    }
}
