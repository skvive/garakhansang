import SwiftUI

struct BrandHeader: View {
    var body: some View {
        HStack(spacing: 12) {
            Image("OfficialLogo")
                .resizable().scaledToFit().frame(width: 56, height: 56)
                .accessibilityLabel("가락한상 공식 로고")
            VStack(alignment: .leading, spacing: 2) {
                Text("가락한상 오더")
                    .font(.title3.weight(.heavy)).foregroundStyle(BrandTheme.brown)
                Text("가락시장 30년 전통의 맛")
                    .font(.caption).foregroundStyle(BrandTheme.muted)
            }
            Spacer(minLength: 4)
            Image(systemName: "bell.badge")
                .font(.title3).foregroundStyle(BrandTheme.muted)
                .accessibilityHidden(true) // decorative placeholder, not an active notification action
        }
        .padding(.horizontal, 18).padding(.vertical, 12)
        .background(.white)
    }
}

struct EmptyViewMessage: View {
    let symbol: String
    let headline: String
    let hint: String
    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: symbol)
                .font(.system(size: 46)).foregroundStyle(BrandTheme.muted)
                .accessibilityHidden(true)
            Text(headline).font(.headline).foregroundStyle(BrandTheme.brown)
            Text(hint).font(.subheadline).foregroundStyle(BrandTheme.muted)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(.horizontal, 25).padding(.vertical, 50)
    }
}

struct ProductRow: View {
    let item: MenuItem
    let isFavorite: Bool
    let quantity: Int
    let onOpen: () -> Void
    let onFavorite: () -> Void
    let onAdd: () -> Void

    var body: some View {
        HStack(spacing: 13) {
            Button(action: onOpen) {
                Image(item.imageName)
                    .resizable().scaledToFill()
                    .frame(width: 118, height: 128).clipped()
                    .clipShape(RoundedRectangle(cornerRadius: 14))
                    .overlay(alignment: .bottomLeading) {
                        Text("AI 콘셉트")
                            .font(.system(size: 10, weight: .bold))
                            .padding(.horizontal, 7).padding(.vertical, 4)
                            .background(.black.opacity(0.66), in: Capsule())
                            .foregroundStyle(.white)
                            .padding(6)
                    }
            }
            .buttonStyle(.plain)
            .accessibilityLabel("\(item.name) 상세 보기, 참고 이미지")
            VStack(alignment: .leading, spacing: 6) {
                Text(item.category)
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundStyle(BrandTheme.sea).lineLimit(1)
                Button(action: onOpen) {
                    Text(item.name)
                        .font(.subheadline.weight(.bold))
                        .foregroundStyle(BrandTheme.brown)
                        .multilineTextAlignment(.leading).lineLimit(2)
                }.buttonStyle(.plain)
                Text("참고가 \(item.priceKRW.krwText)")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(BrandTheme.red)
                Spacer(minLength: 1)
                HStack(spacing: 7) {
                    Button(action: onFavorite) {
                        Image(systemName: isFavorite ? "heart.fill" : "heart")
                            .font(.body.weight(.semibold))
                            .foregroundStyle(isFavorite ? BrandTheme.red : BrandTheme.brown)
                            .frame(width: 44, height: 44)
                            .background(BrandTheme.canvas, in: RoundedRectangle(cornerRadius: 10))
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel(isFavorite ? "\(item.name) 찜 해제" : "\(item.name) 찜하기")
                    Button(action: onAdd) {
                        Text(quantity == 0 ? "미리 담기" : "담기 · \(quantity)")
                            .font(.caption.weight(.bold))
                            .foregroundStyle(.white)
                            .frame(maxWidth: .infinity, minHeight: 44)
                            .background(BrandTheme.brown, in: RoundedRectangle(cornerRadius: 11))
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("\(item.name) 데모 장바구니 담기")
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(11).frame(minHeight: 154)
        .background(.white, in: RoundedRectangle(cornerRadius: 17))
        .overlay(RoundedRectangle(cornerRadius: 17).stroke(BrandTheme.brown.opacity(0.07), lineWidth: 1))
        .accessibilityElement(children: .contain)
    }
}
