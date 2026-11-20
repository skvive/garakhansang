import SwiftUI

struct HomeView: View {
    @EnvironmentObject private var model: ShopViewModel
    @State private var selected: MenuItem?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                BrandHeader()
                hero
                Picker("이용 방식", selection: $model.deliveryMode) {
                    ForEach(ServiceMode.allCases) { mode in
                        Text(mode.rawValue).tag(mode)
                    }
                }
                .pickerStyle(.segmented)
                .padding(.horizontal, 16)
                HStack(spacing: 10) {
                    Image(systemName: "magnifyingglass")
                        .foregroundStyle(BrandTheme.muted)
                    TextField("수산물·회·한상 검색", text: $model.search)
                        .submitLabel(.search)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .accessibilityIdentifier("catalog-search")
                    if !model.search.isEmpty {
                        Button {
                            model.search = ""
                        } label: {
                            Image(systemName: "xmark.circle.fill").foregroundStyle(BrandTheme.muted)
                        }
                        .accessibilityLabel("검색어 지우기")
                    }
                }
                .padding(14)
                .background(.white, in: RoundedRectangle(cornerRadius: 13))
                .padding(.horizontal, 16)
                VStack(alignment: .leading, spacing: 10) {
                    Text("카테고리")
                        .font(.headline).foregroundStyle(BrandTheme.brown).padding(.horizontal, 16)
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 9) {
                            categoryChip("전체", key: nil)
                            ForEach(model.catalog.categories, id: \.self) { category in
                                categoryChip(category, key: category)
                            }
                        }.padding(.horizontal, 16)
                    }
                }
                HStack(alignment: .firstTextBaseline) {
                    Text(model.category ?? "오늘의 추천 메뉴")
                        .font(.title3.weight(.bold)).foregroundStyle(BrandTheme.brown)
                    Spacer()
                    Text("\(model.filteredItems.count)개")
                        .font(.caption).foregroundStyle(BrandTheme.muted)
                }.padding(.horizontal, 16)
                if let error = model.catalogError {
                    EmptyViewMessage(symbol: "exclamationmark.triangle", headline: "상품 자료 확인 필요", hint: error)
                } else if model.filteredItems.isEmpty {
                    EmptyViewMessage(symbol: "magnifyingglass", headline: "검색 결과가 없습니다", hint: "다른 검색어를 입력하거나 전체 카테고리를 선택해 보세요.")
                } else {
                    LazyVStack(spacing: 12) {
                        ForEach(model.filteredItems) { item in
                            ProductRow(item: item,
                                       isFavorite: model.favoriteIDs.contains(item.id),
                                       quantity: model.cart.quantity(for: item.id),
                                       onOpen: { selected = item },
                                       onFavorite: { model.toggleFavorite(item) },
                                       onAdd: { model.addToPreview(item) })
                        }
                    }
                    .padding(.horizontal, 16)
                }
                footer
            }
            .padding(.bottom, 30)
        }
        .background(BrandTheme.canvas.ignoresSafeArea())
        .navigationBarHidden(true)
        .sheet(item: $selected) { item in
            NavigationStack { ProductDetailView(item: item) }
        }
    }

    private var hero: some View {
        ZStack(alignment: .leading) {
            RoundedRectangle(cornerRadius: 21).fill(BrandTheme.cream)
            HStack(spacing: 0) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("가락시장의 신선함을\n오늘도 한 상에")
                        .font(.system(size: 23, weight: .heavy))
                        .foregroundStyle(BrandTheme.brown).fixedSize(horizontal: false, vertical: true)
                    Text("신선한 메뉴를 둘러보세요")
                        .font(.footnote).foregroundStyle(BrandTheme.muted)
                    DemoFlag()
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                Image("FeatureFood")
                    .resizable().scaledToFill()
                    .frame(width: 118, height: 150)
                    .clipped().clipShape(RoundedRectangle(cornerRadius: 15))
                    .accessibilityHidden(true)
            }
            .padding(15)
        }
        .padding(.horizontal, 16)
    }

    private var footer: some View {
        VStack(alignment: .leading, spacing: 5) {
            Label("안내", systemImage: "info.circle")
                .font(.footnote.weight(.bold)).foregroundStyle(BrandTheme.brown)
            Text("메뉴 이미지는 AI 콘셉트 참고용입니다. 표기 가격은 검증 전 참고 금액이며, 실제 판매·배송·결제는 제공하지 않습니다.")
                .font(.caption).foregroundStyle(BrandTheme.muted)
                .fixedSize(horizontal: false, vertical: true)
        }.padding(15).frame(maxWidth: .infinity, alignment: .leading)
            .background(BrandTheme.cream.opacity(0.75), in: RoundedRectangle(cornerRadius: 14))
            .padding(.horizontal, 16)
    }

    private func categoryChip(_ title: String, key: String?) -> some View {
        let active = model.category == key
        return Button { model.chooseCategory(key) } label: {
            Text(title).font(.subheadline.weight(.semibold))
                .foregroundStyle(active ? .white : BrandTheme.brown)
                .padding(.horizontal, 13).padding(.vertical, 10)
                .background(active ? BrandTheme.brown : .white, in: Capsule())
        }.buttonStyle(.plain)
            .accessibilityAddTraits(active ? .isSelected : [])
    }
}
