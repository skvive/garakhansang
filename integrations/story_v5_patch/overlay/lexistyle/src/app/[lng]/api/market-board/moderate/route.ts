import { NextResponse } from "next/server";
import { eq } from "drizzle-orm";
import { db,hasDb } from "@/db";
import { garakBoardPosts } from "@/db/garak-board-schema";
import { requireAdmin } from "@/lib/auth/admin";
export async function POST(req:Request){
 const origin=req.headers.get("origin"),host=req.headers.get("host");
 if(origin&&(!host||new URL(origin).host!==host))return NextResponse.json({error:"Origin mismatch"},{status:403});
 const admin=await requireAdmin();
 // Explicit block: the legacy demo admin account cannot approve real posts.
 if(!admin?.user||String(admin.user.id).startsWith("demo:"))return NextResponse.json({error:"관리자 인증 필요"},{status:403});
 if(!hasDb())return NextResponse.json({error:"DB 미연결"},{status:503});
 let payload:unknown;try{payload=await req.json()}catch{return NextResponse.json({error:"Invalid JSON"},{status:400})}
 const p=payload as {id?:unknown;status?:unknown};
 if(typeof p.id!=="string"||!/^[0-9a-f-]{36}$/i.test(p.id)||!["approved","rejected"].includes(String(p.status)))return NextResponse.json({error:"Invalid payload"},{status:400});
 await db().update(garakBoardPosts).set({status:String(p.status)}).where(eq(garakBoardPosts.id,p.id));
 return NextResponse.json({ok:true,status:p.status});
}
