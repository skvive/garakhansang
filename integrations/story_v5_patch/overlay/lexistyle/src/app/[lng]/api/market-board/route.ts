import { NextResponse } from "next/server";
import { and, desc, eq } from "drizzle-orm";
import { z } from "zod";
import { db, hasDb } from "@/db";
import { garakBoardPosts } from "@/db/garak-board-schema";
import { requireSession } from "@/lib/auth/admin";
const draftSchema=z.object({category:z.enum(["상인","유통업체","협회","요리사"]),title:z.string().trim().min(3).max(90),body:z.string().trim().min(10).max(3000)});
export async function GET(){
 if(!hasDb())return NextResponse.json({items:[],status:"database_unconfigured"});
 try {const items=await db().select({id:garakBoardPosts.id,category:garakBoardPosts.category,title:garakBoardPosts.title,body:garakBoardPosts.body,createdAt:garakBoardPosts.createdAt}).from(garakBoardPosts).where(eq(garakBoardPosts.status,"approved")).orderBy(desc(garakBoardPosts.createdAt)).limit(40);return NextResponse.json({items});}
 catch{return NextResponse.json({items:[],error:"게시판 데이터베이스 설정 확인 필요"},{status:503});}
}
export async function POST(req:Request){
 const origin=req.headers.get("origin"),host=req.headers.get("host");
 if(origin&&(!host||new URL(origin).host!==host))return NextResponse.json({error:"Origin mismatch"},{status:403});
 if(!hasDb())return NextResponse.json({error:"게시판 DB 미연결"},{status:503});
 const session=await requireSession();
 if(!session?.user?.id||session.user.id==="demo:admin")return NextResponse.json({error:"실제 회원 로그인이 필요합니다"},{status:401});
 let input:unknown;try{input=await req.json()}catch{return NextResponse.json({error:"Invalid JSON"},{status:400})}
 const parsed=draftSchema.safeParse(input);if(!parsed.success)return NextResponse.json({error:"입력 항목을 확인하세요"},{status:400});
 try{await db().insert(garakBoardPosts).values({...parsed.data,authorId:String(session.user.id),status:"pending"});return NextResponse.json({status:"pending",message:"관리자 확인 후 공개됩니다"},{status:201});}
 catch{return NextResponse.json({error:"게시물 저장 실패. DB 설정 확인 필요"},{status:503});}
}
