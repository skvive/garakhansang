import SwiftUI

struct ProductDetailView: View {
    let item: MenuItem
    @EnvironmentObject private var model: ShopViewModel
    @Environment(\.dismiss) private var dismiss
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Image(item.imageName)
                    .resizable().scaledToFill()
                    .frame(maxWidth: .infinity).frame(height: 280)
                    .clipped().accessibilityLabel("\(item.name) AI 콘셉트 참고 이미지")
                VStack(alignment: .leading, spacing: 10) {
                    DemoFlag()
                    Text(item.category).font(.subheadline).foregroundStyle(BrandTheme.sea)
                    Text(item.name).font(.title2.bold()).foregroundStyle(BrandTheme.brown)
                    Text("참고 가격 · \(item.priceKRW.krwText)")
                        .font(.title3.weight(.bold)).foregroundStyle(BrandTheme.red)
                    Divider()
                    Text("메뉴 안내").font(.headline).foregroundStyle(BrandTheme.brown)
                    Text(item.description)
                        .font(.body).foregroundStyle(BrandTheme.muted)
                        .fixedSize(horizontal: false, vertical: true)
                    Label("이미지는 AI로 제작한 참고 시안이며 실제 제공 상품 사진이 아닙니다.", systemImage: "info.circle")
                        .font(.footnote).foregroundStyle(BrandTheme.muted)
                        .padding(.top, 4)
                    Button {
                        model.addToPreview(item)
                    } label: {
                        Label("장바구니 미리 담기", systemImage: "bag.badge.plus")
                            .frame(maxWidth: .infinity, minHeight: 52)
                            .foregroundStyle(.white).fontWeight(.bold)
                            .background(BrandTheme.brown, in: RoundedRectangle(cornerRadius: 14))
                    }.padding(.top, 12)
                    Text("실제 주문·결제는 제공하지 않습니다")
                        .font(.caption).foregroundStyle(BrandTheme.red).frame(maxWidth: .infinity)
                }.padding(.horizontal, 20)
            }
            .padding(.bottom, 30)
        }
        .background(BrandTheme.canvas.ignoresSafeArea())
        .navigationTitle("메뉴 상세")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar { ToolbarItem(placement: .navigationBarTrailing) { Button("닫기") { dismiss() } } }
    }
}
