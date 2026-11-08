import Foundation

@main
struct VerifiedCatalogModelsSelfTest {
    static func document(name:String="승인 수산물",price:Int=45000,stock:Int=3,
                         merchant:String="merchant-approved",image:String="https://example.org/real.jpg",
                         approved:Bool=true,checkout:Bool=false) -> [String:Any] {
        let item:[String:Any]=[
            "id":"GYS-099","sku":"GYS-099","merchant_id":merchant,
            "merchant_name":merchant,"name":name,"description":"공식 등록상품",
            "category_id":"seafood","category_name":"수산물","price_krw":price,
            "currency":"KRW","stock":stock,"image_url":image,
            "merchant_verified":approved,"can_checkout":checkout
        ]
        return ["schema_version":1,"source":"verified_neon_release_ready",
                "items":[item],"count":1,"order_service_ready":false,
                "delivery_tracking_ready":false,"refresh_seconds":30]
    }
    static func parse(_ dict:[String:Any]) throws -> VerifiedCatalogEnvelope {
        let data=try JSONSerialization.data(withJSONObject:dict)
        return try VerifiedCatalogPolicy.decode(data)
    }
    static func rejected(_ dict:[String:Any]) {
        do{
            _ = try parse(dict)
            fatalError("Unsafe catalog accepted")
        }catch{
            print("PASS rejected unsafe catalog")
        }
    }
    static func main() throws {
        let ok=try parse(document())
        precondition(ok.items.count==1)
        precondition(ok.items[0].merchant_name=="merchant-approved")
        precondition(ok.items[0].price_krw==45000)
        precondition(ok.items[0].image_url.scheme=="https")
        rejected(document(price:0))
        rejected(document(stock:0))
        rejected(document(image:"http://example.org/demo.jpg"))
        rejected(document(image:"https://user:pass@example.org/file.jpg"))
        rejected(document(approved:false))
        rejected(document(checkout:true))
        var wrong=document();wrong["order_service_ready"]=true;rejected(wrong)
        wrong=document();wrong["source"]="synthetic_preview";rejected(wrong)
        wrong=document();wrong["count"]=100;rejected(wrong)
        wrong=document()
        if let a=wrong["items"] as? [[String:Any]], let only=a.first {
            wrong["items"]=[only,only];wrong["count"]=2
        }
        rejected(wrong)
        print("PASS 11 verified iOS catalog model and safety scenarios")
    }
}
