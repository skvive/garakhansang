import Foundation
import SwiftUI

/// Shared read-only catalog synced from the same release gate as the GarakHansang site.
@MainActor
final class VerifiedCatalogStore: ObservableObject {
    @Published private(set) var products: [VerifiedCatalogProduct] = []
    @Published private(set) var status: String = "공식 상품 정보를 확인 중입니다."
    @Published private(set) var refreshing = false
    @Published private(set) var lastUpdated: Date?
    @Published private(set) var cart: [String: Int] = [:]
    @Published var search = ""
    @Published var merchantFilter = ""
    private var etag: String?
    private let endpoint = "https://garakmall.lexid.site/api/mobile/v1/catalog"
    private let cartKey = "garak_verified_preview_cart_v1"

    init() {
        if let stored = UserDefaults.standard.dictionary(forKey: cartKey) as? [String: Int] {
            cart = stored.filter { $0.value > 0 && $0.value <= 99 && !$0.key.isEmpty }
        }
    }

    var merchants: [String] { Array(Set(products.map(\.merchant_name))).sorted() }
    var filtered: [VerifiedCatalogProduct] {
        let q = search.trimmingCharacters(in: .whitespacesAndNewlines)
        return products.filter {
            (merchantFilter.isEmpty || $0.merchant_name == merchantFilter) &&
            (q.isEmpty || $0.name.localizedStandardContains(q) ||
                $0.merchant_name.localizedStandardContains(q) ||
                $0.category_name.localizedStandardContains(q))
        }
    }

    func item(_ sku: String) -> VerifiedCatalogProduct? { products.first { $0.sku == sku } }
    var previewCount: Int { cart.values.reduce(0,+) }
    var previewSubtotal: Int {
        cart.reduce(0) { sum, pair in
            guard let product = item(pair.key), pair.value <= product.stock else { return sum }
            return sum + product.price_krw * pair.value
        }
    }
    func add(_ product: VerifiedCatalogProduct, quantity: Int) {
        guard let latest = item(product.sku), latest.stock > 0 else { return }
        let next = min(99,min(latest.stock,(cart[product.sku] ?? 0) + max(1,quantity)))
        cart[product.sku] = next
        save()
    }
    func change(_ sku: String, delta: Int) {
        let old = cart[sku] ?? 0
        let cap = item(sku).map { min(99,$0.stock) } ?? old
        let next = max(0,min(cap,old+delta))
        if next == 0 { cart.removeValue(forKey: sku) } else { cart[sku] = next }
        save()
    }
    func remove(_ sku: String) { cart.removeValue(forKey: sku);save() }
    private func save() { UserDefaults.standard.set(cart,forKey:cartKey) }

    func refresh() async {
        guard !refreshing else { return }
        guard let url = URL(string:endpoint) else {
            products=[];status="서버 주소를 확인할 수 없습니다.";return
        }
        refreshing=true
        defer { refreshing=false }
        var request=URLRequest(url:url,cachePolicy:.reloadIgnoringLocalCacheData,
                               timeoutInterval:11)
        request.httpMethod="GET"
        request.setValue("application/json",forHTTPHeaderField:"Accept")
        request.setValue("no-store",forHTTPHeaderField:"Cache-Control")
        if let etag = etag, !etag.isEmpty { request.setValue(etag,forHTTPHeaderField:"If-None-Match") }
        do {
            let (data,response)=try await URLSession.shared.data(for:request)
            guard let http=response as? HTTPURLResponse else {throw URLError(.badServerResponse)}
            if http.statusCode==304 && lastUpdated != nil {
                lastUpdated=Date();status="공식 상품 최신 상태 확인 완료"
                return
            }
            guard http.statusCode==200 else {throw URLError(.badServerResponse)}
            let parsed=try VerifiedCatalogPolicy.decode(data)
            products=parsed.items
            etag=http.value(forHTTPHeaderField:"ETag")
            lastUpdated=Date()
            status=parsed.items.isEmpty
                ? "아직 판매 승인된 공식 상품이 없습니다."
                : "공식 입점 상품 \(parsed.count)종 최신 확인"
        } catch {
            // Never keep a stale stock count visible after a failed network refresh.
            products=[]
            etag=nil
            lastUpdated=nil
            status="공식 상품 서버 동기화 실패 · 연결을 확인해 주세요"
        }
    }
}

struct VerifiedLiveCatalogScreen: View {
    @EnvironmentObject var live: VerifiedCatalogStore
    private let columns = [GridItem(.flexible(),spacing:12),GridItem(.flexible(),spacing:12)]

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment:.leading,spacing:16) {
                    header
                    HStack(spacing:9) {
                        Image(systemName:live.products.isEmpty ? "checkmark.shield" : "checkmark.seal.fill")
                            .foregroundStyle(Brand.brown)
                        Text(live.status).font(.subheadline).foregroundStyle(.secondary)
                        Spacer(minLength:0)
                    }
                    .padding(14).background(Brand.cream,in:RoundedRectangle(cornerRadius:13))
                    TextField("상품명·매장명·카테고리 검색",text:$live.search)
                        .textFieldStyle(.roundedBorder)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    ScrollView(.horizontal,showsIndicators:false) {
                        HStack(spacing:8) {
                            merchantChip("",label:"전체 매장")
                            ForEach(live.merchants,id:\.self) { merchant in
                                merchantChip(merchant,label:merchant)
                            }
                        }
                    }
                    if live.products.isEmpty {
                        EmptyState(title: "공식 판매 상품 등록 준비 중",
                                   systemName:"checkmark.shield",
                                   detail:"홈페이지에서 상인 및 상품 검증이 완료되면 자동으로 표시됩니다. 결제와 배송은 별도 승인 후 제공됩니다.")
                        NavigationLink {
                            MenuScreen()
                        } label: {
                            Label("시연 메뉴 47종 살펴보기",systemImage:"square.grid.2x2")
                                .frame(maxWidth:.infinity,minHeight:52)
                        }.buttonStyle(.bordered).tint(Brand.brown)
                    } else if live.filtered.isEmpty {
                        EmptyState(title:"검색된 상품이 없습니다",systemName:"magnifyingglass",
                                   detail:"매장명이나 상품명을 다시 검색해 주세요.")
                    } else {
                        LazyVGrid(columns:columns,spacing:12){
                            ForEach(live.filtered) { item in
                                NavigationLink {
                                    VerifiedLiveProductScreen(sku:item.sku)
                                } label: {
                                    VerifiedLiveCard(item:item)
                                }.buttonStyle(.plain)
                            }
                        }
                    }
                    Text("승인 상품만 표시됩니다. 재고·가격은 새로고침 시 갱신되며 실제 결제 전 서버 검증이 필요합니다.")
                        .font(.caption).foregroundStyle(.secondary)
                }.padding(16)
            }
            .background(Brand.canvas)
            .navigationTitle("공식 입점 상품")
            .toolbar {
                ToolbarItem(placement:.topBarTrailing) {
                    Button { Task { await live.refresh() } } label: {
                        Image(systemName:"arrow.clockwise")
                    }
                    .disabled(live.refreshing)
                    .accessibilityLabel("공식 상품 새로고침")
                }
            }
            .refreshable { await live.refresh() }
            .task { if live.lastUpdated == nil { await live.refresh() } }
        }
    }

    private var header: some View {
        ZStack(alignment:.leading) {
            RoundedRectangle(cornerRadius:20)
                .fill(LinearGradient(colors:[Brand.brown,Brand.red],startPoint:.topLeading,endPoint:.bottomTrailing))
            VStack(alignment:.leading,spacing:10) {
                Text("GARAKHANSANG · LIVE")
                    .font(.caption.bold()).foregroundStyle(.white.opacity(0.85))
                Text("시장과 연결되는\n새로운 장보기")
                    .font(.system(size:25,weight:.heavy)).foregroundStyle(.white)
                Label("실검증 상품만 표시",systemImage:"checkmark.seal")
                    .font(.caption.bold()).foregroundStyle(Brand.brown)
                    .padding(.horizontal,12).padding(.vertical,8)
                    .background(Brand.cream,in:Capsule())
            }.padding(20)
        }.frame(minHeight:180)
    }
    private func merchantChip(_ key:String,label:String) -> some View {
        Button(label){live.merchantFilter=key}
            .font(.subheadline.bold())
            .foregroundStyle(live.merchantFilter==key ? Color.white : Brand.brown)
            .padding(.horizontal,14).frame(minHeight:44)
            .background(live.merchantFilter==key ? Brand.brown : Brand.cream,in:Capsule())
            .accessibilityAddTraits(live.merchantFilter==key ? .isSelected : [])
    }
}

struct VerifiedLiveCard: View {
    let item:VerifiedCatalogProduct
    var body:some View {
        VStack(alignment:.leading,spacing:8) {
            AsyncImage(url:item.image_url) { phase in
                if let image=phase.image {
                    image.resizable().scaledToFill()
                } else if phase.error != nil {
                    ZStack{Color.gray.opacity(0.12)
                        Text("상품 사진을\n불러올 수 없습니다").font(.caption).multilineTextAlignment(.center)}
                } else {
                    ZStack{Brand.cream;ProgressView()}
                }
            }
            .frame(height:136).frame(maxWidth:.infinity).clipped()
            .clipShape(RoundedRectangle(cornerRadius:12))
            Text(item.merchant_name)
                .font(.caption).foregroundStyle(.secondary).lineLimit(1)
            Text(item.name).font(.subheadline.bold()).foregroundStyle(.primary)
                .lineLimit(2).frame(height:41,alignment:.topLeading)
            Text(item.price_krw.formatted(.number)+"원")
                .font(.headline).foregroundStyle(Brand.red)
            Label("상세 보기",systemImage:"arrow.right")
                .font(.caption.bold()).foregroundStyle(Brand.brown)
                .frame(maxWidth:.infinity,minHeight:44)
                .background(Brand.cream,in:RoundedRectangle(cornerRadius:10))
        }
        .padding(11).background(.white,in:RoundedRectangle(cornerRadius:16))
        .overlay(RoundedRectangle(cornerRadius:16).stroke(Brand.cream,lineWidth:1))
        .accessibilityElement(children:.contain)
    }
}

struct VerifiedLiveProductScreen:View {
    @EnvironmentObject var live:VerifiedCatalogStore
    let sku:String
    @State private var quantity=1
    @State private var added=false
    var body:some View {
        ScrollView {
            if let item=live.item(sku) {
                VStack(alignment:.leading,spacing:16) {
                    AsyncImage(url:item.image_url) { phase in
                        if let image=phase.image {image.resizable().scaledToFill()}
                        else if phase.error != nil {Text("사진 로딩 실패").foregroundStyle(.secondary)}
                        else {ProgressView()}
                    }
                    .frame(height:300).frame(maxWidth:.infinity).clipped()
                    .clipShape(RoundedRectangle(cornerRadius:16))
                    Text("검증된 입점 상품").font(.caption.bold()).foregroundStyle(Brand.brown)
                    Text(item.name).font(.title2.bold())
                    Text(item.price_krw.formatted(.number)+"원")
                        .font(.title.bold()).foregroundStyle(Brand.red)
                    Text(item.merchant_name+" · "+item.category_name)
                        .font(.subheadline).foregroundStyle(.secondary)
                    if !item.description.isEmpty {
                        Text(item.description).font(.body).foregroundStyle(.primary)
                    }
                    HStack {
                        Label("현재 재고 \(item.stock)개",systemImage:"shippingbox")
                        Spacer()
                        Text("KRW").foregroundStyle(.secondary)
                    }.font(.subheadline).padding(14)
                        .background(Brand.cream,in:RoundedRectangle(cornerRadius:12))
                    HStack {
                        Text("미리 담을 수량").font(.headline)
                        Spacer()
                        Button {quantity=max(1,quantity-1)} label:{
                            Image(systemName:"minus.circle").frame(width:44,height:44)
                        }.accessibilityLabel("수량 감소")
                        Text("\(quantity)").font(.headline.monospacedDigit()).frame(minWidth:28)
                        Button {quantity=min(item.stock,min(99,quantity+1))} label:{
                            Image(systemName:"plus.circle.fill").frame(width:44,height:44)
                        }.accessibilityLabel("수량 증가")
                    }.tint(Brand.brown)
                    Button {
                        live.add(item,quantity:quantity)
                        added=true
                    } label: {
                        Label(added ? "장바구니에 미리 담았습니다" : "장바구니에 미리 담기",
                              systemImage:added ? "checkmark.circle" : "cart.badge.plus")
                            .frame(maxWidth:.infinity,minHeight:52)
                    }.buttonStyle(.borderedProminent).tint(Brand.brown)
                    Text("실제 주문·결제·배달 접수는 운영 계정 및 배송 API 검증 후 연결됩니다.")
                        .font(.caption).foregroundStyle(.secondary)
                }.padding(18)
            } else {
                EmptyState(title:"현재 판매 가능 목록에서 제외된 상품입니다",
                           systemName:"exclamationmark.triangle",
                           detail:"승인 상태나 재고가 변경됐을 수 있습니다. 새로고침 후 확인해 주세요.")
            }
        }
        .background(Brand.canvas)
        .navigationTitle("상품 상세")
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct VerifiedLiveCartSection:View {
    @EnvironmentObject var live:VerifiedCatalogStore
    var body:some View {
        if !live.cart.isEmpty {
            VStack(alignment:.leading,spacing:13) {
                Text("공식 상품 장바구니 · 미리보기")
                    .font(.headline)
                Text("서버에서 다시 확인한 가격·재고이며 실제 주문이나 결제는 발생하지 않습니다.")
                    .font(.caption).foregroundStyle(.secondary)
                ForEach(live.cart.keys.sorted(),id:\.self) { sku in
                    if let item=live.item(sku),let count=live.cart[sku] {
                        HStack(spacing:9) {
                            VStack(alignment:.leading,spacing:5) {
                                Text(item.name).font(.subheadline.bold())
                                Text(item.price_krw.formatted(.number)+"원 × \(count)")
                                    .font(.caption).foregroundStyle(.secondary)
                            }
                            Spacer()
                            Button {live.change(sku,delta:-1)} label:{
                                Image(systemName:"minus.circle").frame(width:44,height:44)
                            }.accessibilityLabel(item.name+" 수량 감소")
                            Button {live.change(sku,delta:1)} label:{
                                Image(systemName:"plus.circle.fill").frame(width:44,height:44)
                            }.accessibilityLabel(item.name+" 수량 증가")
                        }.tint(Brand.brown).padding(12)
                            .background(.white,in:RoundedRectangle(cornerRadius:12))
                    } else {
                        HStack {
                            Text(sku+" · 승인 취소 또는 서버 연결 대기")
                                .font(.caption).foregroundStyle(Brand.red)
                            Spacer()
                            Button("삭제"){live.remove(sku)}
                                .frame(minHeight:44)
                        }.padding(12).background(.white,in:RoundedRectangle(cornerRadius:12))
                    }
                }
                HStack {
                    Text("참고 소계").font(.headline)
                    Spacer()
                    Text(live.previewSubtotal.formatted(.number)+"원")
                        .font(.title3.bold()).foregroundStyle(Brand.red)
                }
                Text("배송료와 최종 결제금액은 표시하지 않습니다. 실주문 기능은 검증 전까지 차단됩니다.")
                    .font(.caption).foregroundStyle(.secondary)
            }.padding(15).background(Brand.cream,in:RoundedRectangle(cornerRadius:16))
        }
    }
}

struct VerifiedDeliveryStatusScreen:View {
    var body:some View {
        VStack(spacing:15) {
            Image(systemName:"truck.box").font(.system(size:45)).foregroundStyle(Brand.brown)
            Text("배송 조회").font(.title2.bold())
            Text("주문·결제 및 배송 상태는 고객 본인 인증 후에만 조회할 수 있습니다. 현재 네이티브 주문·배송 API는 미연결 상태입니다.")
                .multilineTextAlignment(.center).foregroundStyle(.secondary)
            if let url=URL(string:"https://garakmall.lexid.site/mypage.html"){
                Link(destination:url) {
                    Label("홈페이지 마이페이지에서 확인",systemImage:"safari")
                        .frame(maxWidth:.infinity,minHeight:52)
                }.buttonStyle(.borderedProminent).tint(Brand.brown)
            }
        }.padding(24).frame(maxWidth:.infinity,maxHeight:.infinity)
            .background(Brand.canvas).navigationTitle("배송 조회")
    }
}


struct VerifiedLiveHomeTile:View {
    @EnvironmentObject var live:VerifiedCatalogStore
    var body:some View {
        NavigationLink {
            VerifiedLiveCatalogScreen()
        } label: {
            HStack(spacing:14) {
                ZStack {
                    RoundedRectangle(cornerRadius:13).fill(Brand.cream)
                    Image(systemName:"checkmark.seal.fill")
                        .font(.system(size:25)).foregroundStyle(Brand.brown)
                }.frame(width:58,height:58)
                VStack(alignment:.leading,spacing:5){
                    Text("공식 입점 새상품").font(.headline).foregroundStyle(.primary)
                    Text(live.products.isEmpty
                         ? "승인 매장 준비 중 · 서버 자동 갱신"
                         : "현재 승인 상품 \(live.products.count)종 · 실시간 연동")
                        .font(.caption).foregroundStyle(.secondary)
                    Text("홈페이지와 같은 판매 승인 DB")
                        .font(.caption.bold()).foregroundStyle(Brand.brown)
                }
                Spacer(minLength:0)
                Image(systemName:"chevron.right").foregroundStyle(Brand.brown)
            }.padding(15)
                .background(.white,in:RoundedRectangle(cornerRadius:16))
                .overlay(RoundedRectangle(cornerRadius:16).stroke(Brand.cream,lineWidth:1))
        }.buttonStyle(.plain)
        .accessibilityLabel("공식 입점 상품, 홈페이지 승인 DB 최신 정보 열기")
    }
}
