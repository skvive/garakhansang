import SwiftUI

struct CartView: View {
    @EnvironmentObject private var model: ShopViewModel
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                DemoFlag().padding(.top, 16)
                if model.cartItems.isEmpty {
                    EmptyViewMessage(symbol: "bag", headline: "장바구니가 비어 있어요", hint: "홈에서 메뉴를 담아 미리 확인해 보세요.")
                    Button("상품 둘러보기") { model.tab = .home }
                        .fontWeight(.semibold).foregroundStyle(BrandTheme.red)
                        .frame(maxWidth: .infinity)
                } else {
                    ForEach(model.cartItems) { item in cartRow(item) }
                    VStack(spacing: 10) {
                        HStack {
                            Text("참고 상품 합계")
                            Spacer()
                            Text(model.previewTotal.krwText).fontWeight(.bold)
                        }
                        HStack {
                            Text("배달비·할인")
                            Spacer()
                            Text("권역 미확인").foregroundStyle(BrandTheme.muted)
                        }
                        Divider()
                        Button(action: {}) {
                            Label("실제 주문은 아직 지원되지 않습니다", systemImage: "lock.fill")
                                .font(.subheadline.weight(.bold))
                                .frame(maxWidth: .infinity, minHeight: 52)
                        }
                        .disabled(true)
                        .buttonStyle(.borderedProminent)
                        .tint(BrandTheme.brown)
                        Text("상품명·가격·배송 가능 권역·결제 연동이 승인되기 전에는 주문을 받을 수 없습니다.")
                            .font(.caption).foregroundStyle(BrandTheme.muted)
                            .multilineTextAlignment(.center)
                    }
                    .padding(17).background(.white, in: RoundedRectangle(cornerRadius: 17))
                }
            }.padding(.horizontal, 16).padding(.bottom, 28)
        }
        .background(BrandTheme.canvas.ignoresSafeArea())
        .navigationTitle("장바구니 미리보기")
    }

    private func cartRow(_ item: MenuItem) -> some View {
        HStack(alignment: .top, spacing: 12) {
            Image(item.imageName)
                .resizable().scaledToFill().frame(width: 86, height: 86).clipped()
                .clipShape(RoundedRectangle(cornerRadius: 12))
                .accessibilityHidden(true)
            VStack(alignment: .leading, spacing: 5) {
                Text(item.name).font(.subheadline.weight(.bold)).foregroundStyle(BrandTheme.brown)
                Text("참고가 \(item.priceKRW.krwText)")
                    .font(.caption).foregroundStyle(BrandTheme.muted)
                HStack(spacing: 0) {
                    Button { model.subtractFromPreview(item) } label: {
                        Image(systemName: "minus").frame(width: 42, height: 42)
                    }.accessibilityLabel("\(item.name) 수량 감소")
                    Text("\(model.cart.quantity(for: item.id))")
                        .frame(minWidth: 35).font(.subheadline.monospacedDigit())
                    Button { model.addToPreview(item) } label: {
                        Image(systemName: "plus").frame(width: 42, height: 42)
                    }.disabled(model.cart.quantity(for: item.id) >= PreviewCart.maximumPerItem)
                        .accessibilityLabel("\(item.name) 수량 증가")
                }
                .foregroundStyle(BrandTheme.brown)
                .background(BrandTheme.cream, in: RoundedRectangle(cornerRadius: 9))
            }
            Spacer(minLength: 0)
            Button { model.removeFromPreview(item) } label: {
                Image(systemName: "xmark.circle.fill").foregroundStyle(BrandTheme.muted)
                    .frame(width: 36, height: 36)
            }.accessibilityLabel("\(item.name) 장바구니에서 삭제")
        }
        .padding(13).background(.white, in: RoundedRectangle(cornerRadius: 15))
    }
}
