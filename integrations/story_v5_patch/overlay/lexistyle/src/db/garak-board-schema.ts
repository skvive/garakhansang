import {pgTable, text, timestamp, uuid} from "drizzle-orm/pg-core";
export const garakBoardPosts = pgTable("garak_board_posts",{
 id: uuid("id").primaryKey().defaultRandom(),
 authorId:text("author_id").notNull(),
 category:text("category").notNull(),
 title:text("title").notNull(),
 body:text("body").notNull(),
 status:text("status").notNull().default("pending"),
 createdAt:timestamp("created_at",{withTimezone:true}).notNull().defaultNow(),
});
