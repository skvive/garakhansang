import SwiftUI

private enum Tab: Int { case home, menu, cart, orders, mine }

struct RootTabView: View {
    @EnvironmentObject var store: CatalogStore
    // iPhone Simulator screen-by-screen QA. Normal installation starts at Home.
    @State private var tab: Tab =
        Tab(rawValue: Int(ProcessInfo.processInfo.environment["GHS_QA_TAB"] ?? "") ?? 0) ?? .home

    var body: some View {
        TabView(selection: $tab) {
            HomeScreen(onBrowse: { tab = .menu }).tabItem { Label("홈", systemImage: "house.fill") }.tag(Tab.home)
            MenuScreen().tabItem { Label("메뉴", systemImage: "square.grid.2x2.fill") }.tag(Tab.menu)
            DemoCartScreen().tabItem { Label("장바구니", systemImage: "cart.fill") }.tag(Tab.cart)
            OrdersScreen().tabItem { Label("주문내역", systemImage: "clock.arrow.circlepath") }.tag(Tab.orders)
            MineScreen(onBrowse: { tab = .menu }).tabItem { Label("마이", systemImage: "person.crop.circle") }.tag(Tab.mine)
        }
        .tint(Brand.brown)
    }
}

struct HomeScreen: View {
    @EnvironmentObject var store: CatalogStore
    var onBrowse: () -> Void
    private let grid = [GridItem(.flexible(), spacing: 12), GridItem(.flexible(), spacing: 12)]

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    HStack(spacing: 12) {
                        BundledImage(filename: "garakhansang-symbol.png", subdirectory: "Brand", contentMode: .fit)
                            .frame(width: 53, height: 53).clipShape(RoundedRectangle(cornerRadius: 14))
                        VStack(alignment: .leading, spacing: 3) {
                            Text("가락한상 오더").font(.system(size: 24, weight: .heavy))
                            Text("가락시장 30년 전통의 맛").font(.caption).foregroundStyle(.secondary)
                        }
                        Spacer()
                        Image(systemName: "bell.slash").foregroundStyle(Brand.brown)
                            .accessibilityLabel("알림 서비스 준비 중")
                    }.padding(.top, 14)
                    hero
                    DemoNotice()
                    VStack(alignment: .leading, spacing: 12) {
                        Text("이용 방식 미리보기").font(.title3.bold())
                        Picker("이용 방식", selection: $store.fulfillment) {
                            ForEach(CatalogStore.Fulfillment.allCases) { mode in Text(mode.rawValue).tag(mode) }
                        }.pickerStyle(.segmented)
                        Text("주소 조회 및 배달 가능 지역 판정은 아직 연결되지 않았습니다.")
                            .font(.caption).foregroundStyle(.secondary)
                    }
                    HStack {
                        Text("추천 메뉴 살펴보기").font(.title3.bold())
                        Spacer()
                        Button("전체 47종") { onBrowse() }
                            .font(.subheadline.bold()).foregroundStyle(Brand.red)
                    }
                    LazyVGrid(columns: grid, spacing: 14) {
                        ForEach(Array(store.items.prefix(8))) { item in
                            NavigationLink { ItemDetailScreen(item: item) } label: { MenuCard(item: item) }
                                .buttonStyle(.plain)
                        }
                    }
                    Button(action: onBrowse) {
                        HStack { Text("전체 메뉴 47종 둘러보기"); Spacer(); Image(systemName: "arrow.right") }
                            .font(.headline).padding(16).frame(maxWidth: .infinity)
                            .foregroundStyle(.white).background(Brand.brown, in: RoundedRectangle(cornerRadius: 14))
                    }.accessibilityHint("판매 전 참고 상품 목록으로 이동")
                }
                .padding(.horizontal, 18).padding(.bottom, 26)
            }
            .background(Brand.canvas)
            .toolbar(.hidden, for: .navigationBar)
        }
    }

    private var hero: some View {
        ZStack(alignment: .leading) {
            RoundedRectangle(cornerRadius: 22)
                .fill(LinearGradient(colors: [Brand.brown, Brand.red], startPoint: .topLeading, endPoint: .bottomTrailing))
            HStack(spacing: 12) {
                VStack(alignment: .leading, spacing: 12) {
                    Text("가락시장의 맛을\n한 화면에 담다")
                        .font(.system(size: 25, weight: .heavy)).foregroundStyle(.white)
                    Text("47개 메뉴 · 12개 카테고리")
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundStyle(.white.opacity(0.85))
                    Text("시연 카탈로그")
                        .font(.caption.bold()).padding(.horizontal, 12).padding(.vertical, 7)
                        .foregroundStyle(Brand.brown).background(Brand.cream, in: Capsule())
                }
                Spacer(minLength: 0)
                BundledImage(filename: "garakhansang-logo.png", subdirectory: "Brand", contentMode: .fit)
                    .frame(width: 125, height: 125)
                    .accessibilityHidden(true)
            }.padding(18)
        }.frame(height: 187)
    }
}

struct MenuScreen: View {
    @EnvironmentObject var store: CatalogStore
    private let grid = [GridItem(.flexible(), spacing: 12), GridItem(.flexible(), spacing: 12)]
    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        categoryButton(nil, name: "전체")
                        ForEach(store.categories, id: \.self) { c in categoryButton(c, name: c) }
                    }.padding(.horizontal, 16).padding(.vertical, 12)
                }
                ScrollView {
                    VStack(alignment: .leading, spacing: 14) {
                        DemoNotice(compact: true)
                        Text("총 \(store.displayedItems.count)개 참고 메뉴")
                            .font(.subheadline).foregroundStyle(.secondary)
                        if let error = store.loadError {
                            EmptyState(title: error, systemName: "exclamationmark.triangle", detail: "시연 데이터 복구 후 이용해 주세요.")
                        } else if store.displayedItems.isEmpty {
                            EmptyState(title: "검색 결과가 없습니다", systemName: "magnifyingglass", detail: "다른 검색어나 카테고리를 선택해 보세요.")
                        } else {
                            LazyVGrid(columns: grid, spacing: 15) {
                                ForEach(store.displayedItems) { item in
                                    NavigationLink { ItemDetailScreen(item: item) } label: { MenuCard(item: item) }
                                        .buttonStyle(.plain)
                                }
                            }
                        }
                    }.padding(16)
                }.background(Brand.canvas)
            }
            .navigationTitle("메뉴")
            .searchable(text: $store.searchQuery, prompt: "메뉴명 검색")
        }
    }
    private func categoryButton(_ category: String?, name: String) -> some View {
        let selected = store.selectedCategory == category
        return Button(name) { store.selectCategory(category) }
            .font(.system(size: 13, weight: .semibold))
            .foregroundStyle(selected ? Color.white : Brand.brown)
            .padding(.horizontal, 13).padding(.vertical, 10)
            .background(selected ? Brand.brown : Brand.cream, in: Capsule())
            .accessibilityAddTraits(selected ? .isSelected : [])
    }
}

struct MenuCard: View {
    @EnvironmentObject var store: CatalogStore
    let item: CatalogItem
    var body: some View {
        VStack(alignment: .leading, spacing: 9) {
            ZStack(alignment: .topTrailing) {
                BundledImage(filename: item.image, subdirectory: "MenuImages")
                    .frame(maxWidth: .infinity).frame(height: 135).clipped()
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                Button { store.toggleFavorite(item) } label: {
                    Image(systemName: store.favorites.contains(item.id) ? "heart.fill" : "heart")
                        .foregroundStyle(Brand.red).frame(width: 44, height: 44)
                        .background(Color.white.opacity(0.94), in: Circle())
                }
                .buttonStyle(.plain)
                .accessibilityLabel(store.favorites.contains(item.id) ? "찜 해제" : "찜하기")
                .padding(5)
            }
            Text(item.name).font(.system(size: 14, weight: .bold))
                .foregroundStyle(.primary).lineLimit(2).frame(height: 38, alignment: .topLeading)
            Text(item.won).font(.system(size: 16, weight: .heavy)).foregroundStyle(Brand.brown)
            HStack(spacing: 5) {
                Text("AI 이미지").font(.system(size: 10, weight: .medium))
                    .foregroundStyle(.secondary)
                Spacer()
                Button { store.addDemo(item) } label: { Image(systemName: "plus.circle.fill").font(.title3).foregroundStyle(Brand.red).frame(width: 44,height:44) }
                    .buttonStyle(.plain).accessibilityLabel("\(item.name) 시연 장바구니에 추가")
            }
        }
        .padding(10).background(Color.white, in: RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).strokeBorder(Brand.cream.opacity(0.8)))
        .accessibilityElement(children: .contain)
    }
}

struct ItemDetailScreen: View {
    @EnvironmentObject var store: CatalogStore
    let item: CatalogItem
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                BundledImage(filename: item.image, subdirectory: "MenuImages")
                    .frame(maxWidth: .infinity).frame(height: 300).clipped()
                    .clipShape(RoundedRectangle(cornerRadius: 16))
                DemoNotice(compact: true)
                Text(item.category).font(.subheadline).foregroundStyle(Brand.teal)
                Text(item.name).font(.title2.bold())
                Text(item.won).font(.title2.bold()).foregroundStyle(Brand.red)
                if !item.description.isEmpty { Text(item.description).font(.body).foregroundStyle(.secondary) }
                Text("이 이미지는 AI로 제작한 참고 시안이며 실제 판매 상품 사진이 아닙니다.")
                    .font(.caption).foregroundStyle(.secondary)
                HStack(spacing: 12) {
                    Button { store.toggleFavorite(item) } label: {
                        Label(store.favorites.contains(item.id) ? "찜 해제" : "찜하기", systemImage: store.favorites.contains(item.id) ? "heart.fill" : "heart")
                            .frame(maxWidth: .infinity, minHeight: 50)
                    }.buttonStyle(.bordered)
                    Button { store.addDemo(item) } label: {
                        Label("시연 장바구니 담기", systemImage: "cart.badge.plus")
                            .frame(maxWidth: .infinity, minHeight: 50)
                    }.buttonStyle(.borderedProminent).tint(Brand.brown)
                }
                if let route = VerifiedMarketNavigation.directions(travelMode: .walking) {
                    Link(destination: route.url) {
                        Label("가락시장 위치만 확인", systemImage: "mappin.and.ellipse")
                            .frame(maxWidth: .infinity, minHeight: 48)
                    }
                    .buttonStyle(.bordered)
                    .accessibilityHint("실매장 주소 확인 전에는 가락시장 기준 위치만 안내합니다")
                }
                Text("실제 판매가·재고·배송 가능 여부가 검증되지 않아 주문 및 결제 버튼을 제공하지 않습니다.")
                    .font(.caption).foregroundStyle(.secondary)
            }.padding(18)
        }
        .background(Brand.canvas)
        .navigationTitle("메뉴 상세")
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct DemoCartScreen: View {
    @EnvironmentObject var store: CatalogStore
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    DemoNotice()
                    if store.cartItems.isEmpty {
                        EmptyState(title: "장바구니가 비었습니다", systemName: "cart", detail: "메뉴에서 시연용 상품을 담아보세요.")
                    } else {
                        ForEach(store.cartItems) { line in
                            let item = line.item
                            let quantity = line.quantity
                            HStack(spacing: 12) {
                                BundledImage(filename: item.image, subdirectory: "MenuImages")
                                    .frame(width: 72, height: 72).clipped().clipShape(RoundedRectangle(cornerRadius: 9))
                                VStack(alignment: .leading, spacing: 7) {
                                    Text(item.name).font(.subheadline.bold()).lineLimit(2)
                                    Text(item.won).font(.subheadline).foregroundStyle(Brand.brown)
                                }
                                Spacer()
                                VStack(spacing: 2) {
                                    Button { store.addDemo(item) } label: { Image(systemName: "plus.circle").frame(width: 44,height:44) }
                                        .accessibilityLabel("\(item.name) 시연 수량 추가")
                                    Text("\(quantity)").font(.subheadline.bold())
                                    Button { store.decrementDemo(item) } label: { Image(systemName: "minus.circle").frame(width: 44,height:44) }
                                        .accessibilityLabel("\(item.name) 시연 수량 감소")
                                }.tint(Brand.brown)
                            }.padding(12).background(.white, in: RoundedRectangle(cornerRadius: 13))
                        }
                        HStack {
                            Text("시연 합계").font(.headline)
                            Spacer()
                            Text(store.subtotal.formatted(.number) + "원")
                                .font(.title3.bold()).foregroundStyle(Brand.red)
                        }.padding(16).background(Brand.cream, in: RoundedRectangle(cornerRadius: 13))
                        Text("합계는 시연용 계산이며 결제 금액이 아닙니다.")
                            .font(.caption).foregroundStyle(.secondary)
                        Button(role: .destructive) { store.clearDemo() } label: {
                            Label("시연 장바구니 비우기", systemImage: "trash")
                                .frame(maxWidth: .infinity, minHeight: 48)
                        }.buttonStyle(.bordered)
                    }
                }.padding(16)
            }.background(Brand.canvas)
            .navigationTitle("장바구니 (\(store.itemCount))")
        }
    }
}

struct OrdersScreen: View {
    var body: some View {
        NavigationStack {
            VStack(spacing: 18) {
                DemoNotice()
                Spacer()
                Image(systemName: "receipt").font(.system(size: 48)).foregroundStyle(Brand.brown)
                Text("실제 주문 내역은 없습니다").font(.title3.bold())
                Text("시연 앱에서는 주문을 접수하거나 결제하지 않습니다.")
                    .font(.subheadline).foregroundStyle(.secondary).multilineTextAlignment(.center)
                Spacer()
            }.padding(20).frame(maxWidth: .infinity).background(Brand.canvas)
                .navigationTitle("주문내역")
        }
    }
}

struct MineScreen: View {
    @EnvironmentObject var store: CatalogStore
    var onBrowse: () -> Void
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    BundledImage(filename: "garakhansang-logo.png", subdirectory: "Brand", contentMode: .fit)
                        .frame(width: 160,height: 160).padding(.top, 10)
                    Text("가락한상 오더").font(.title2.bold())
                    Text("로그인과 회원 기능은 정식 출시 시 제공됩니다.")
                        .font(.subheadline).foregroundStyle(.secondary)
                    DemoNotice()
                    VStack(alignment: .leading, spacing: 14) {
                        Label("찜한 메뉴: \(store.savedItems.count)종", systemImage: "heart")
                        Label("시연 장바구니: \(store.itemCount)개", systemImage: "cart")
                        Label("실제 계정 및 결제정보는 저장되지 않습니다", systemImage: "lock.shield")
                    }.font(.subheadline).frame(maxWidth: .infinity, alignment: .leading)
                        .padding(20).background(.white, in: RoundedRectangle(cornerRadius: 16))
                    Button(action: onBrowse) { Label("전체 메뉴 보기", systemImage: "square.grid.2x2")
                        .frame(maxWidth: .infinity, minHeight: 52) }
                        .buttonStyle(.borderedProminent).tint(Brand.brown)
                    if let route = VerifiedMarketNavigation.directions(travelMode: .driving) {
                        Link(destination: route.url) {
                            Label("가락시장 길찾기 · Google 지도", systemImage: "map")
                                .frame(maxWidth: .infinity, minHeight: 52)
                        }
                        .buttonStyle(.bordered).tint(Brand.brown)
                        .accessibilityHint("매장 좌표가 승인되지 않아 실제 판매점이 아닌 가락시장 기준으로 안내합니다")
                    }
                    Text("매장 좌표 및 고객 배송지는 아직 검증되지 않아 경로에 포함하지 않습니다.")
                        .font(.caption).foregroundStyle(.secondary)
                    Text("본 앱은 iOS 시연용 네이티브 프로젝트입니다.\nAI 콘셉트 메뉴 이미지 · 판매 승인 전 상품 표시")
                        .font(.caption).foregroundStyle(.secondary).multilineTextAlignment(.center)
                }.padding(18)
            }.background(Brand.canvas).navigationTitle("마이")
        }
    }
}

struct EmptyState: View {
    let title: String
    let systemName: String
    let detail: String
    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: systemName).font(.system(size: 34)).foregroundStyle(Brand.brown)
            Text(title).font(.headline).multilineTextAlignment(.center)
            Text(detail).font(.subheadline).foregroundStyle(.secondary).multilineTextAlignment(.center)
        }.padding(.vertical, 48).frame(maxWidth: .infinity)
    }
}
