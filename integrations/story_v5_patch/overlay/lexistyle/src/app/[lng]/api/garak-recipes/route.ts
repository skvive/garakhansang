import { NextResponse } from "next/server";
import { GARAK_RECIPES } from "@/lib/garak/recipes";
export function GET(req:Request){
  const url = new URL(req.url); const cat = url.searchParams.get("category");
  const q = (url.searchParams.get("q")??"").trim().slice(0,60).toLocaleLowerCase("ko-KR");
  const data=GARAK_RECIPES.filter(r=>(!cat||r.category===cat)&&(!q||r.title.toLocaleLowerCase("ko-KR").includes(q)||r.main.toLocaleLowerCase("ko-KR").includes(q)));
  return NextResponse.json({total:data.length, editorial_status:"편집 초안",items:data.map(({id,title,category,main,time,sku})=>({id,title,category,main,time,sku}))},{headers:{"Cache-Control":"public,max-age=120"}});
}
