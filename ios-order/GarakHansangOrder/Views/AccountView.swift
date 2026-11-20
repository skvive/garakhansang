import SwiftUI

struct AccountView: View {
    @EnvironmentObject private var model: ShopViewModel
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                HStack(spacing: 15) {
                    Image("OfficialLogo").resizable().scaledToFit().frame(width: 70, height: 70)
                        .accessibilityLabel("가락한상 공식 로고")
                    VStack(alignment: .leading, spacing: 6) {
                        Text("가락한상 오더").font(.title3.bold()).foregroundStyle(BrandTheme.brown)
                        Text("iPhone 네이티브 시연 앱").font(.subheadline).foregroundStyle(BrandTheme.muted)
                        DemoFlag()
                    }
                }
                .padding(16).frame(maxWidth: .infinity, alignment: .leading)
                .background(.white, in: RoundedRectangle(cornerRadius: 17))
                VStack(alignment: .leading, spacing: 14) {
                    Text("계정 서비스").font(.headline).foregroundStyle(BrandTheme.brown)
                    Label("Google 로그인 — 개발 서버 연결 전", systemImage: "person.crop.circle.badge.xmark")
                    Label("주문 내역 — 실제 주문 기능 미제공", systemImage: "list.bullet.rectangle")
                    Label("배송 주소 — 수집 및 저장하지 않음", systemImage: "location.slash")
                }
                .font(.subheadline)
                .foregroundStyle(BrandTheme.muted)
                .padding(17).frame(maxWidth: .infinity, alignment: .leading)
                .background(.white, in: RoundedRectangle(cornerRadius: 17))
                VStack(alignment: .leading, spacing: 10) {
                    Text("서비스 준비 상태").font(.headline).foregroundStyle(BrandTheme.brown)
                    status("상품 47개·카테고리 12개", ready: true)
                    status("찜·장바구니 오프라인 시연", ready: true)
                    status("매장·재고·배송권역 승인", ready: false)
                    status("Google 인증·실결제·환불", ready: false)
                    status("실주문·배차·정산", ready: false)
                }
                .padding(17).frame(maxWidth: .infinity, alignment: .leading)
                .background(.white, in: RoundedRectangle(cornerRadius: 17))
                Text("버전 0.1.0 · iOS 데모 / Android v1.11 데이터 기반. 이 앱은 결제, 로그인, 위치 권한 또는 고객 개인정보를 수집하지 않습니다.")
                    .font(.caption).foregroundStyle(BrandTheme.muted)
                    .padding(.horizontal, 7)
            }
            .padding(16)
        }
        .background(BrandTheme.canvas.ignoresSafeArea())
        .navigationTitle("마이")
    }

    private func status(_ label: String, ready: Bool) -> some View {
        Label(label, systemImage: ready ? "checkmark.circle.fill" : "clock")
            .font(.subheadline)
            .foregroundStyle(ready ? BrandTheme.positive : BrandTheme.muted)
            .padding(.vertical, 2)
    }
}
