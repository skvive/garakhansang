import type { Metadata } from 'next';
import { requireAdmin } from '@/lib/auth/admin';
import { notFound } from 'next/navigation';

/** Human-reviewed migration bridge. No backend credentials are placed in browser code.
 * GARAK_ADMIN_URL is the separately hosted, TLS-protected administrator service.
 * Production SSO and Neon source-of-truth synchronization are NOT yet implemented.
 */
export const metadata: Metadata = { title: '가락한상 운영센터', robots: { index: false, follow: false } };
export const dynamic = 'force-dynamic';
export default async function GarakOperationsPage() {
  const session = await requireAdmin();
  if (!session) notFound();
  const configured = process.env.GARAK_ADMIN_URL ?? '';
  const url = configured.startsWith('https://') ? configured : null;
  return (
    <main className="mx-auto max-w-3xl px-5 py-12">
      <p className="text-sm font-bold text-orange-700">관리자 전용 · 통합 운영</p>
      <h1 className="mt-3 text-3xl font-bold">가락한상 운영센터</h1>
      <p className="mt-4 leading-7 text-slate-700">
        재고·상품·상인·주문·배송·레시피·홍보·통계 관리를 위한 운영센터 연결 페이지입니다.
        베타 서버의 테스트 데이터와 실제 쇼핑몰 주문·결제 데이터는 서로 분리되어 있습니다.
      </p>
      {url ? (
        <a href={url} rel="noopener noreferrer" target="_blank" className="mt-7 inline-flex rounded-xl bg-slate-900 px-5 py-3 font-semibold text-white">
          별도 인증이 필요한 운영센터 열기
        </a>
      ) : (
        <p className="mt-7 rounded-xl border border-amber-200 bg-amber-50 p-5">
          GARAK_ADMIN_URL(HTTPS) 미설정. 프로덕션에 관리자 서버를 직접 노출하지 마세요.
        </p>
      )}
    </main>
  );
}
