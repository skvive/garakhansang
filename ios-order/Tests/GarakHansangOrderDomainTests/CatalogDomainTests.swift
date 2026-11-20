import XCTest
@testable import GarakHansangOrderDomain

final class CatalogDomainTests: XCTestCase {
    private func catalog() throws -> MenuCatalog {
        let url = try XCTUnwrap(Bundle.module.url(forResource: "menu_catalog", withExtension: "json"))
        return try CatalogStore.decodeAndValidate(Data(contentsOf: url))
    }

    func testOriginalCatalogHas47Items12Categories() throws {
        let c = try catalog()
        XCTAssertEqual(c.items.count, 47)
        XCTAssertEqual(c.categories.count, 12)
        XCTAssertTrue(c.notForLiveSales)
        XCTAssertTrue(c.items.allSatisfy { !$0.isOrderable && $0.imageIsAIConcept })
        XCTAssertEqual(c.items.first?.id, "GH-001")
        XCTAssertEqual(c.items.last?.id, "GH-047")
    }

    func testSearchAndCategoryFiltering() throws {
        let c = try catalog()
        XCTAssertEqual(c.filtered(category: nil, search: " ").count, 47)
        XCTAssertFalse(c.filtered(category: nil, search: "연어").isEmpty)
        XCTAssertFalse(c.filtered(category: "오늘의 한상", search: "한상").isEmpty)
        XCTAssertTrue(c.filtered(category: "사이드", search: "찾을 수 없는 상품").isEmpty)
        XCTAssertTrue(c.filtered(category: nil, search: "없는 텍스트xyz").isEmpty)
    }

    func testInvalidLiveCatalogRejected() throws {
        let data = try XCTUnwrap(String(data: Data(contentsOf: XCTUnwrap(Bundle.module.url(forResource: "menu_catalog", withExtension: "json"))), encoding: .utf8))
        let unsafe = data.replacingOccurrences(of: "\"not_for_live_sales\": true", with: "\"not_for_live_sales\": false")
        XCTAssertThrowsError(try CatalogStore.decodeAndValidate(Data(unsafe.utf8)))
        let orderable = data.replacingOccurrences(of: "\"is_orderable\": false", with: "\"is_orderable\": true", range: data.range(of: "\"is_orderable\": false"))
        XCTAssertThrowsError(try CatalogStore.decodeAndValidate(Data(orderable.utf8)))
    }

    func testDuplicateIDsRejected() throws {
        let input = Data(#"{"brand":"test","version":"1","not_for_live_sales":true,"items":[{"id":"A","category":"C","name":"N","price_krw":20,"description":"D","image":"menu_01.jpg","catalog_visibility":"needs_merchandising_approval","image_is_ai_concept":true,"is_orderable":false},{"id":"A","category":"C","name":"N","price_krw":20,"description":"D","image":"menu_02.jpg","catalog_visibility":"needs_merchandising_approval","image_is_ai_concept":true,"is_orderable":false}]}"#.utf8)
        XCTAssertThrowsError(try CatalogStore.decodeAndValidate(input)) { error in
            XCTAssertEqual(error as? CatalogValidationError, .duplicateID)
        }
    }

    func testPreviewCartCannotPlaceLiveOrder() throws {
        let c = try catalog(), item = try XCTUnwrap(c.items.first)
        var cart = PreviewCart()
        XCTAssertEqual(cart.count, 0)
        for _ in 0..<20 { XCTAssertTrue(cart.add(item)) }
        XCTAssertFalse(cart.add(item))
        XCTAssertEqual(cart.quantity(for: item.id), 20)
        XCTAssertEqual(cart.total(catalog: c), 20 * item.priceKRW)
        cart.subtract(id: item.id)
        XCTAssertEqual(cart.count, 19)
        cart.remove(id: item.id)
        XCTAssertEqual(cart.count, 0)
    }

    func testPreviewCartClearsAndDoesNotPersist() throws {
        let c = try catalog()
        var cart = PreviewCart()
        XCTAssertTrue(cart.add(c.items[3]))
        cart.clear()
        XCTAssertEqual(cart.count, 0)
        XCTAssertTrue(PreviewCart().quantities.isEmpty)
    }
}
